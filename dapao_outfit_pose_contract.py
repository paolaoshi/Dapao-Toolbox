"""Resolve observed framing labels without another model or image mutation."""
import re
import json

BOUNDARIES = ("CHEST", "WAIST", "HIPS", "THIGHS", "KNEES", "FULL")


def tag(text, name):
    match = re.search(r"<" + name + r">\s*([^<>]*?)\s*</" + name + r">", text, re.I | re.S)
    return match.group(1).strip() if match else ""


def boundary(text, name):
    value = tag(text, name).upper()
    return value if value in BOUNDARIES else None


def resolve_boundary(source_plan, pose_plan, framing_policy="closer"):
    source = boundary(source_plan, "source_crop")
    target = boundary(pose_plan, "target_crop")
    requested = boundary(source_plan, "requested_crop")
    known = [x for x in (source, target) if x]
    resolved = requested or ((target or source) if framing_policy == "target" else
                             (min(known, key=BOUNDARIES.index) if source and known else None))
    return source, target, requested, resolved


def resolve_contract(source_plan, pose_plan, framing_policy="closer"):
    source, target, requested, resolved = resolve_boundary(source_plan, pose_plan, framing_policy)
    geometry = tag(pose_plan, "geometry")
    if "POSE_SKIP" in pose_plan or not geometry:
        return "POSE_SKIP", f"source={source}; target={target}; requested={requested}; invalid pose contract"
    crops = {
        "CHEST": "a close portrait ending across the chest",
        "WAIST": "a waist-up portrait, with the waist at the bottom image boundary",
        "HIPS": "a head-to-hips portrait, with the hips at the bottom image boundary",
        "THIGHS": "a head-to-thighs shot, cut through the thighs at the bottom image boundary",
        "KNEES": "a head-to-knees shot, cut at the knees at the bottom image boundary",
        "FULL": "a full-body shot with the complete figure in frame",
    }
    framing = ("Final composition MUST be " + crops[resolved] + ". " if resolved else
               "Keep the source camera distance and body crop; no inferred zoom-out. ")
    prompt = framing + ((
        "The target pose determines camera perspective, subject scale and body coverage, unless explicitly overridden above. "
        "The original photograph's crop does not restrict newly visible body regions. Rebuild one anatomically coherent body "
        "in the target arrangement; remove the previous limb arrangement, rather than adding limbs over it. "
        "Dress newly visible regions with the selected outfit evidence; the guide supplies geometry, not clothing or bare-skin requirements. "
        "Preserve natural occlusion and a plausible support surface. Do not force hidden limbs into view. "
        "Target geometry: " + geometry
    ) if framing_policy == "target" else (
        "Reframe the same scene to this shot, not just the canvas ratio. The guide may show more body than this final crop; "
        "apply its geometry only inside the resolved frame, leaving the remaining limbs outside the photograph. "
        "Never shrink the person to fit an entire guide or outfit. Exactly one person. "
        "Target geometry (subordinate to the final crop): " + geometry
    ))
    return prompt, f"source={source}; target={target}; requested={requested}; resolved={resolved}; policy={framing_policy}"


def crop_box(plan, crop):
    try:
        boxes = json.loads(tag(plan, 'frame_boxes'))
        box = boxes.get(crop)
        if not isinstance(box, list) or len(box) != 4:
            return None
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in box):
            return None
        x1, y1, x2, y2 = box
        if not all(0 <= v <= 1000 for v in box) or x2 - x1 < 100 or y2 - y1 < 100:
            return None
        # Anatomical crops must not run backwards (waist above chest, hips above waist).
        # Reject inconsistent selected boxes rather than cutting through the wrong body site.
        for other_name, other in boxes.items():
            if other_name not in BOUNDARIES or not isinstance(other, list) or len(other) != 4:
                continue
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in other):
                continue
            if BOUNDARIES.index(other_name) < BOUNDARIES.index(crop) and other[3] > y2 + 20:
                return None
            if BOUNDARIES.index(other_name) > BOUNDARIES.index(crop) and other[3] < y2 - 20:
                return None
        return tuple(v / 1000 for v in box)
    except (ValueError, TypeError, AttributeError):
        return None


def crop_reference(image, box):
    if box is None:
        return image
    height, width = image.shape[1:3]
    x1, y1, x2, y2 = box
    # A small context margin protects fingertips / hair and avoids a hard joint cut.
    x1, y1 = max(0, int((x1 - .02) * width)), max(0, int((y1 - .02) * height))
    x2, y2 = min(width, int((x2 + .02) * width)), min(height, int((y2 + .02) * height))
    return image[:, y1:y2, x1:x2, :].contiguous()


class DapaoOutfitPoseContract:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"source_plan": ("STRING", {"forceInput": True}),
                             "pose_plan": ("STRING", {"forceInput": True}),
                             "pose_image": ("IMAGE",), "appearance_image": ("IMAGE",),
                             "source_image": ("IMAGE",)},
                "optional": {"framing_policy": (["closer", "target"], {"default": "closer"})}}

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("姿势与取景指令", "取景判定", "同取景姿势参考", "同取景人物参考")
    FUNCTION = "resolve"
    CATEGORY = "Dapao/换装"

    def resolve(self, source_plan, pose_plan, pose_image, appearance_image, source_image, framing_policy="closer"):
        prompt, diagnostic = resolve_contract(source_plan, pose_plan, framing_policy)
        source, target, requested, resolved = resolve_boundary(source_plan, pose_plan, framing_policy)
        pose_box = crop_box(pose_plan, resolved) if resolved and target and BOUNDARIES.index(resolved) < BOUNDARIES.index(target) else None
        source_box = crop_box(source_plan, resolved) if resolved and source and BOUNDARIES.index(resolved) < BOUNDARIES.index(source) else None
        # Custom canvases may change image coordinates; do not apply source-photo boxes blindly.
        ref_ratio = source_image.shape[2] / source_image.shape[1]
        appearance_ratio = appearance_image.shape[2] / appearance_image.shape[1]
        if requested or abs(appearance_ratio / ref_ratio - 1) > .05:
            source_box = None
        if prompt == 'POSE_SKIP':
            pose_box = source_box = None
        diagnostic += f'; pose_box={pose_box}; source_box={source_box}'
        return prompt, diagnostic, crop_reference(pose_image, pose_box), crop_reference(appearance_image, source_box)

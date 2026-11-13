"""Prepare paired face crops, a local editing prompt and a mask in base-image coordinates."""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import torch
import folder_paths


@lru_cache(maxsize=1)
def parser():
    import onnxruntime as ort
    model = Path(folder_paths.models_dir) / "segformer_b2_clothes/onnx/model.onnx"
    if not model.is_file():
        raise ValueError(f"缺少人像分区模型：{model}")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    return ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])


def parse_parts(rgb):
    image = cv2.resize(rgb, (512, 512), interpolation=cv2.INTER_LINEAR)
    image = (image - np.float32([.485, .456, .406])) / np.float32([.229, .224, .225])
    session = parser()
    logits = session.run(None, {session.get_inputs()[0].name: image.transpose(2, 0, 1)[None]})[0][0]
    return cv2.resize(logits.argmax(0).astype(np.uint8), (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)


def box(mask):
    x, y, w, h = cv2.boundingRect(mask.astype(np.uint8))
    return x, y, x + w, y + h


def numbered(image, boxes, selected):
    canvas = (image * 255).clip(0, 255).astype(np.uint8)
    for number, (x, y, r, b) in enumerate(boxes, 1):
        color = (40, 240, 100) if number == selected else (255, 190, 20)
        cv2.rectangle(canvas, (x, y), (r, b), color, 3)
        cv2.putText(canvas, str(number), (x, max(y + 21, 22)), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 4)
        cv2.putText(canvas, str(number), (x, max(y + 21, 22)), cv2.FONT_HERSHEY_SIMPLEX, .8, color, 2)
    return torch.from_numpy(canvas).float().div(255)[None]


def analyze(tensor, detector, index, manual, label, hair):
    if tensor.shape[0] != 1:
        raise ValueError(f"{label} 请使用单张图片")
    rgb = tensor[0, :, :, :3].detach().cpu().numpy()
    H, W = rgb.shape[:2]
    boxes = sorted([tuple(map(int, seg.bbox)) for seg in detector.detect(tensor, .30, 0, 1.0)[1]], key=lambda b: (b[0], b[1]))
    hand = None
    if manual is not None and manual.max().item() > .05:
        hand = manual.reshape(-1, *manual.shape[-2:])[0].cpu().numpy() > .05
        if hand.shape != (H, W):
            raise ValueError(f"{label} 手工遮罩尺寸与原图不符")
    if not boxes:
        if hand is None:
            raise ValueError(f"{label} 未检测到脸。可在该图的遮罩编辑器涂出脸或头部后重试。")
        boxes = [box(hand)]
    if index > len(boxes):
        raise ValueError(f"{label} 检测到 {len(boxes)} 张脸，请选择有效编号（从左到右，0 为最大脸）。")
    if not index and hand is not None:
        index = 1 + max(range(len(boxes)), key=lambda i: hand[boxes[i][1]:boxes[i][3], boxes[i][0]:boxes[i][2]].sum())
    if not index:
        index = 1 + max(range(len(boxes)), key=lambda i: (boxes[i][2]-boxes[i][0])*(boxes[i][3]-boxes[i][1]))
    x, y, r, b = bounds = boxes[index-1]
    w, h = max(r-x, 1), max(b-y, 1)
    cx, cy = (x+r)/2, (y+b)/2
    # Expand the parsing region whenever connected hair reaches an interior crop edge.
    scale = 1.
    while True:
        x0, y0 = max(0, int(x-1.4*w*scale)), max(0, int(y-1.4*h*scale))
        x1, y1 = min(W, int(r+1.4*w*scale)), min(H, int(b+2.5*h*scale))
        parts = parse_parts(rgb[y0:y1, x0:x1])
        yy, xx = np.ogrid[y0:y1, x0:x1]
        near_face = ((xx-cx)/(.65*w))**2 + ((yy-cy)/(.68*h))**2 <= 1
        owner = np.ones(parts.shape, dtype=bool)
        for other in boxes:
            if other == bounds:
                continue
            ox, oy, rr, bb = other
            owner &= ((xx-cx)**2+(yy-cy)**2) <= ((xx-(ox+rr)/2)**2+(yy-(oy+bb)/2)**2)
        skin = (parts == 11) & near_face & owner
        glasses = (parts == 3) & near_face & owner
        candidate = (parts == 2) & owner
        _, ids = cv2.connectedComponents(candidate.astype(np.uint8))
        seed = (abs(xx-cx) < .86*w) & (yy > y-.9*h) & (yy < b+.15*h)
        keep = np.unique(ids[seed & candidate])
        locks = np.isin(ids, keep) if keep.size else np.zeros_like(owner)
        touches = ((x0 and locks[:,0].any()) or (x1<W and locks[:,-1].any()) or
                   (y0 and locks[0].any()) or (y1<H and locks[-1].any()))
        if not (hair and touches):
            break
        scale *= 2
    def full(local):
        result = np.zeros((H,W),np.uint8)
        result[y0:y1,x0:x1] = local
        return result
    if not skin.any():
        skin = (((xx-cx)/(.45*w))**2 + ((yy-cy)/(.48*h))**2 <= 1) & owner
    # Measure exposed skin inside the upper head silhouette. Background above
    # a close-cropped head must not dilute the fraction.
    crown = (abs(xx-cx) < .28*w) & (yy >= y-.35*h) & (yy < y+.13*h) & owner
    crown_skin = crown & (parts == 11)
    visible = crown & np.isin(parts,[1,2,11])
    exposed = crown_skin.sum() > .035*w*h and crown_skin.sum() > .60*visible.sum()
    scalp = ((parts == 11) & owner & (abs(xx-cx)<.75*w)
             & (yy >= y-.65*h) & (yy<y+.37*h)) if exposed else np.zeros_like(locks)
    return dict(detached_hair=full(candidate & ~locks), scalp=full(scalp), rgb=rgb, face=full(skin | glasses), hair=full(locks), glasses=full(glasses),
                background=full((parts == 0) & owner), hat=full((parts == 1) & owner & (abs(xx-cx)<1.4*w) & (yy<b)), bounds=bounds, manual=hand, preview=numbered(rgb,boxes,index), others=[item for item in boxes if item != bounds])


def accessory_area(part, kind):
    x,y,r,b = part["bounds"]
    w,h = r-x,b-y
    region = np.zeros_like(part["face"])
    if kind == "帽子":
        return part["hat"]
    if kind == "头饰":
        cv2.ellipse(region,(round((x+r)/2),round(y+.02*h)),(max(1,round(.83*w)),max(1,round(.62*h))),0,0,360,1,-1)
    elif kind == "耳饰":
        for side in (x,r):
            cv2.ellipse(region,(side,round(y+.66*h)),(max(1,round(.21*w)),max(1,round(.34*h))),0,0,360,1,-1)
    else:
        cv2.ellipse(region,(round((x+r)/2),round(b+.32*h)),(max(1,round(.7*w)),max(1,round(.34*h))),0,0,360,1,-1)
    return region


def hair_guide(base, ref, transform, hair, hat_mode, cleanup):
    height,width = base["face"].shape
    src = np.zeros_like(ref["face"])
    old = np.zeros_like(base["face"])
    if hair:
        src |= ref["hair"] | ref["scalp"]
        old |= base["hair"]
    if hat_mode == "跟随脸图":
        src |= ref["hat"]
    if hat_mode != "保留底图":
        old |= base["hat"]
    aligned = cv2.warpAffine(src,transform,(width,height),flags=cv2.INTER_NEAREST)
    radius=max(2,round((base["bounds"][2]-base["bounds"][0])*.045))
    kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1))
    clear=cv2.dilate(old,kernel) * (1-aligned) * (1-base["face"])
    if hat_mode == "保留底图":
        clear *= 1-base["hat"]
        aligned *= 1-base["hat"]
    rgb = base["rgb"].copy()
    # The cleanup halo grants paste permission on background; it is not old hair.
    crown_clear = clear.copy() if hair and ref["scalp"].any() else None
    if hair and cleanup and old.any() and base["manual"] is None:
        face_width=base["bounds"][2]-base["bounds"][0]
        distance=cv2.distanceTransform(1-old,cv2.DIST_L2,5)
        halo=(distance <= face_width*1.6*cleanup/100) & (base["background"]>0)
        halo &= (aligned==0) & (base["face"]==0) & (base["hat"]==0)
        # Remove narrow light or dark streaks from the background conditioning
        # while keeping broad window edges and the original scene lighting.
        gray=cv2.cvtColor((rgb*255).astype(np.uint8),cv2.COLOR_RGB2GRAY)
        size=2*max(2,round(face_width*.012))+1
        disk=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(size,size))
        streak=np.maximum(cv2.morphologyEx(gray,cv2.MORPH_TOPHAT,disk),
                          cv2.morphologyEx(gray,cv2.MORPH_BLACKHAT,disk))
        marks=cv2.dilate((streak>13).astype(np.uint8),np.ones((3,3),np.uint8))*halo
        if marks.any():
            pixels=(rgb*255).astype(np.uint8)
            filled=cv2.inpaint(pixels,marks,3,cv2.INPAINT_TELEA)
            rgb[marks>0]=filled[marks>0]/255.
        clear |= halo.astype(np.uint8)
        # Hair split by a shoulder is still old hair. Include nearby detached
        # parsing components in the paste mask, even when clothing lies between
        # the two islands. Never use this shortcut to assign another person's hair.
        if not base["others"] and base["detached_hair"].any():
            count, ids = cv2.connectedComponents(base["detached_hair"])
            gap = max(2, face_width * .32 * cleanup / 100)
            close = np.unique(ids[(ids>0) & (distance<=gap)])
            if close.size:
                pieces = np.isin(ids,close) & (distance<face_width*.85)
                pieces = cv2.dilate(pieces.astype(np.uint8),kernel)
                clear |= pieces * (1-aligned) * (1-base["face"]) * (1-base["hat"])
    if hair and ref["scalp"].any():
        # Where old hair extends beyond the new crown, provide nearby scene
        # colours as a guide. Qwen reconstructs the texture before compositing.
        x,y,r,b = base["bounds"]
        rows=np.arange(height)[:,None]
        erase=(crown_clear>0) & (rows < y+.48*(b-y))
        bg=(base["background"]>0) & (old==0) & (crown_clear==0)
        if erase.any() and bg.any():
            _,labels=cv2.distanceTransformWithLabels((~bg).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
            colors=np.zeros((labels.max()+1,3),np.float32)
            colors[labels[bg]]=rgb[bg]
            fade=np.clip((y+.48*(b-y)-rows)/max(1,.18*(b-y)),0,1)
            weight=(erase*fade).astype(np.float32)[:,:,None]
            rgb+=weight*(colors[labels]-rgb)
    guide=cv2.warpAffine(ref["rgb"],transform,(width,height))
    blend=cv2.GaussianBlur(aligned.astype(np.float32),(0,0),max(1,radius/3))[:,:,None]
    return rgb*(1-blend)+guide*blend, clear|aligned


def registered_expression(crop, ref, base, x, y, alpha, amount, use_mouth, use_eyes):
    # Eye corners define position/roll; the nose fixes the projected side of
    # each triangle. Mouth corners position the smile without fixing lip opening.
    from .dapao_face_harmonize import face_landmarks
    a = face_landmarks(ref["rgb"],ref["bounds"])[:,:2].astype(np.float32)
    b = face_landmarks(base["rgb"],base["bounds"])[:,:2].astype(np.float32) - np.float32([x,y])
    h,w = crop.shape[:2]
    fw = max(1,base["bounds"][2]-base["bounds"][0])
    yy,xx = np.ogrid[:h,:w]
    scene = cv2.GaussianBlur(crop,(0,0),max(2,.075*fw))
    result = crop
    features = []
    if use_eyes:
        features.extend([([36,39,30],.095),([42,45,30],.095)])
    if use_mouth:
        features.append(([48,54,30],.14))
    for indices,height in features:
        tri,output = a[indices],b[indices]
        # Do not magnify a largely occluded feature from an almost side-on face.
        if min(cv2.contourArea(tri),cv2.contourArea(output))<4:
            continue
        affine = cv2.getAffineTransform(tri,output)
        scales = np.linalg.svd(affine[:,:2],compute_uv=False)
        if np.linalg.det(affine[:,:2])<=0 or scales[0]>3*scales[1]:
            continue
        aligned = cv2.warpAffine(ref["rgb"],affine,(w,h))
        face = cv2.warpAffine(ref["face"],affine,(w,h),flags=cv2.INTER_NEAREST)
        center = output[:2].mean(0)
        width = max(3,.85*np.linalg.norm(output[1]-output[0]))
        oval = ((xx-center[0])/width)**2 + ((yy-center[1])/max(2,height*fw))**2
        weight = (amount*np.clip(2*(1-oval),0,1)*alpha*face).astype(np.float32)[:,:,None]
        detail = aligned - cv2.GaussianBlur(aligned,(0,0),max(2,.075*fw))
        result = result*(1-weight) + np.clip(scene+detail,0,1)*weight
    return result


def expression_guide(crop, ref, base, transform, x, y, alpha, amount, use_mouth, use_eyes, follow_base):
    """Supply the visible expression as a soft visual cue in base-face coordinates."""
    landmark_file = Path(folder_paths.models_dir) / "insightface/models/buffalo_l/1k3d68.onnx"
    if follow_base and landmark_file.is_file():
        return registered_expression(crop, ref, base, x, y, alpha, amount, use_mouth, use_eyes)
    target = transform.copy()
    target[:,2] -= [x,y]
    h,w = crop.shape[:2]
    aligned = cv2.warpAffine(ref["rgb"],target,(w,h))
    donor_skin = cv2.warpAffine(ref["face"],target,(w,h),flags=cv2.INTER_NEAREST)
    left,top,right,bottom=base["bounds"]
    fw,fh=max(1,right-left),max(1,bottom-top)
    yy,xx=np.ogrid[:h,:w]
    dx=(xx+x-(left+right)/2)/fw
    dy=(yy+y-top)/fh
    weight=np.zeros((h,w),np.float32)
    if use_mouth:
        weight=np.maximum(weight,np.clip(2.5*(1-(dx/.39)**2-((dy-.73)/.24)**2),0,1))
    if use_eyes:
        weight=np.maximum(weight,np.clip(2*(1-(dx/.50)**2-((dy-.40)/.19)**2),0,1))
    weight=(weight*amount*alpha*donor_skin).astype(np.float32)[:,:,None]
    sigma=max(2,.17*fw)
    # Keep the local illumination of the scene around the transferred features.
    detail=aligned-cv2.GaussianBlur(aligned,(0,0),sigma)
    cue=np.clip(cv2.GaussianBlur(crop,(0,0),sigma)+detail,0,1)
    return crop*(1-weight)+cue*weight


def pad_box(bounds, shape, padding):
    x,y,r,b=bounds
    H,W=shape[:2]
    return max(0,x-padding),max(0,y-padding),min(W,r+padding),min(H,b+padding)


def sized(image, pixels):
    h,w=image.shape[:2]
    scale=min((pixels/(w*h))**.5, 1536/max(h,w))
    dims=tuple(max(32,round(v*scale/32)*32) for v in (w,h))
    result=cv2.resize(image,dims,interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_CUBIC)
    return torch.from_numpy(result.clip(0,1))[None]


def face_cover_instruction(mode, base, ref):
    if mode == "去掉口罩":
        return "摘除口罩，清除面料、褶皱和两侧耳带，显露自然完整的鼻尖、双唇、脸颊与下巴。"
    source = ref if mode == "跟随脸图" else base
    x,y,right,bottom = source["bounds"]
    region = source["rgb"][y:bottom,x:right]
    labels = parse_parts(region)
    h,w = labels.shape
    mouth = labels[int(.55*h):max(int(.83*h),int(.55*h)+1),int(.32*w):max(int(.8*w),int(.32*w)+1)]
    # The installed clothing parser assigns mask fabric to garment classes.
    fabric = np.isin(mouth, [4,5,6,7,8,10,17])
    origin = "图2" if mode == "跟随脸图" else "图1"
    if fabric.mean() > .5:
        return f"成图人物必须佩戴{origin}中的同款口罩，面料覆盖整个鼻尖、嘴巴和下巴，清晰复现口罩的颜色、边缘、褶皱与耳带。被遮挡的鼻唇不可见。"
    return f"鼻口的显露与遮挡严格按{origin}呈现，还原露出的鼻尖、双唇和下巴，不从另一张图带入口鼻配饰。"


def lower_face_region(part):
    x, y, right, bottom = part["bounds"]
    w, h = max(1, right-x), max(1, bottom-y)
    region = np.zeros(part["face"].shape, np.uint8)
    cv2.ellipse(region, (round(x+.5*w), round(y+.67*h)),
                (max(1,round(.64*w)), max(1,round(.52*h))), 0, 0, 360, 1, -1)
    return region


def expression_masks(part, crop, x, y):
    """Tight action cues, used only for model conditioning; never for compositing."""
    from .dapao_face_harmonize import face_landmarks
    l,t,r,b=part["bounds"]
    fw,fh=max(1,r-l),max(1,b-t)
    masks=[np.zeros(crop.shape[:2],np.uint8) for _ in range(2)]
    status=""
    points=None
    if (Path(folder_paths.models_dir)/"insightface/models/buffalo_l/1k3d68.onnx").is_file():
        pts=face_landmarks(part["rgb"],part["bounds"])[:,:2]-[x,y]
        mw=np.linalg.norm(pts[54]-pts[48])
        if np.isfinite(pts).all() and .15*fw<mw<.85*fw and .15*fw<np.linalg.norm(pts[45]-pts[36])<1.05*fw:
            points=pts
    if points is not None:
        for mask,groups in zip(masks,[[(48,60)],[(36,42),(42,48),(17,22),(22,27)]]):
            for a,b1 in groups:
                cv2.fillConvexPoly(mask,cv2.convexHull(np.rint(points[a:b1]).astype(np.int32)),1)
        v=points[54]-points[48]
        normal=np.array([-v[1],v[0]])/mw
        gap=np.median(np.abs((points[[67,66,65]]-points[[61,62,63]])@normal))/mw
        if gap<.048:status="双唇闭合，唇缝连续，不露齿。"
    else:
        cv2.ellipse(masks[0],(round((l+r)/2-x),round(t+.73*fh-y)),(max(1,round(.23*fw)),max(1,round(.075*fh))),0,0,360,1,-1)
    result=[]
    for i,mask in enumerate(masks):
        n=max(1,round(fw*(.033 if i==0 else .012)))
        mask=cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*n+1,2*n+1)))
        result.append(cv2.GaussianBlur(mask.astype(np.float32),(0,0),max(.75,n*.60)))
    return *result,status


def soften_inner_face(crop, base, x, y, edit_alpha, strength):
    """Reduce identity cues only inside the chosen face in the model input."""
    left, top, right, bottom = base["bounds"]
    width, height = max(1,right-left), max(1,bottom-top)
    yy, xx = np.ogrid[:crop.shape[0], :crop.shape[1]]
    dx = (xx + x - (left + right) / 2) / (.48 * width)
    dy = (yy + y - (top + .53 * height)) / (.46 * height)
    weight = np.clip((1 - dx*dx - dy*dy) * 3, 0, 1)
    skin = base["face"][y:y+crop.shape[0], x:x+crop.shape[1]]
    weight = (.94 * strength * weight * skin * edit_alpha).astype(np.float32)[:, :, None]
    blurred = cv2.GaussianBlur(crop, (0, 0), max(1, width * .095))
    return crop + weight * (blurred - crop)


def has_eyewear(source):
    if "_eyewear" in source:
        return source["_eyewear"]
    x, y, r, b = source["bounds"]
    w, h = max(1,r-x), max(1,b-y)
    eye_interior = None
    def evidence(mask):
        nonlocal eye_interior
        count=np.count_nonzero(mask)
        if count < max(4,round(w*h*.008)):
            return False
        if eye_interior is None:
            eye_interior=np.zeros(mask.shape,np.uint8)
            if (Path(folder_paths.models_dir)/"insightface/models/buffalo_l/1k3d68.onnx").is_file():
                from .dapao_face_harmonize import face_landmarks
                points=face_landmarks(source["rgb"],source["bounds"])[:,:2]-[x,y]
                for eye in (points[36:42],points[42:48]):
                    cv2.fillConvexPoly(eye_interior, np.rint(eye).astype(np.int32), 1)
                radius=max(1,round(.02*w))
                eye_interior=cv2.dilate(eye_interior,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,)*2))
        # Isolated pupils/lids can be labelled as lenses by the garment parser.
        return np.count_nonzero(mask & (eye_interior==0)) >= max(4,.30*count,.003*w*h)
    band = source["glasses"][y:y + max(1,round(.68*h)), x:r]
    if evidence(band>0):
        source["_eyewear"]=True
        return True
    # Clothing segmentation loses fine frames on wide hairstyle crops. Check
    # again close to this face, counting only pixels within the upper face.
    rgb = source["rgb"]
    l,t = max(0,int(x-.28*w)),max(0,int(y-.38*h))
    rr,bb = min(rgb.shape[1],int(r+.28*w)),min(rgb.shape[0],int(b+.18*h))
    if rr <= l or bb <= t:
        return False
    labels = parse_parts(rgb[t:bb,l:rr])
    band = labels[y-t:y-t+band.shape[0], x-l:r-l]
    source["_eyewear"]=bool(evidence(band==3))
    return source["_eyewear"]


def eyewear_instruction(mode, base, ref):
    if mode == "去掉眼镜":
        return "移除镜框、镜片和镜腿，补全眼周肤色与自然眉眼。"
    follow = mode == "跟随脸图"
    source = ref if follow else base
    origin = "图2" if follow else "图1"
    if has_eyewear(source):
        return f"沿用{origin}人物佩戴的眼镜，镜架透视与头部一致，每片镜片仅透出其后对应的眼睛，越过脸缘处透出现场背景。"
    # Fine frames can produce no labels, or just one reflected highlight.
    # Treat this as unknown and leave the decision to the unmodified photo.
    return (f"以{origin}原始照片核对双眼至两侧太阳穴：看见镜框、鼻桥或镜腿时完整重建同款双侧眼镜；"
            f"只有{origin}确实未佩戴时才呈现裸眼。镜片透明，勿复制孤立的反光色块。")


def skin_color_hint(base):
    """Measure visible base skin inside the selected face, avoiding glasses and background."""
    x,y,r,b = base["bounds"]
    rgb = base["rgb"][y:b,x:r]
    skin = (base["face"][y:b,x:r]>0) & (base["glasses"][y:b,x:r]==0)
    if not rgb.size or not skin.any():
        return ""
    patch = cv2.resize(rgb,(96,96),interpolation=cv2.INTER_AREA)
    keep = cv2.resize(skin.astype(np.uint8),(96,96),interpolation=cv2.INTER_NEAREST).astype(bool)
    lab = cv2.cvtColor(patch,cv2.COLOR_RGB2LAB)
    yy,xx = np.indices(keep.shape)
    sample = keep & (xx>16) & (xx<80) & (yy>15) & (yy<72)
    sample &= (lab[:,:,0]>18) & (lab[:,:,0]<94) & (lab[:,:,1]>4)
    if sample.sum()<160:
        return ""
    yellowness = np.median(lab[:,:,2][sample])
    if yellowness < -2:
        return "底图可见面部皮肤实测偏冷，沿用耳颈的冷调，不用背景或脸图的暖色给皮肤染色。"
    return "以底图可见皮肤与耳颈为色调基准，背景颜色不能代表整张脸的光色。"


def cheek_paste_margin(mask, guard, bounds, strength):
    """Move only the lateral cheek seam out of the old silhouette before compositing."""
    x,y,r,b = bounds
    fw,fh = max(1,r-x),max(1,b-y)
    reach = min(48., .085*fw*np.clip(strength/100.,0.,1.))
    if reach < 1 or not np.any(mask >= .95):
        return mask
    yy,xx = np.ogrid[:mask.shape[0],:mask.shape[1]]
    side = np.abs((xx-(x+r)*.5)/fw)
    row = (yy-y)/fh
    def ramp(v):
        v = np.clip(v,0.,1.); return v*v*(3.-2.*v)
    zone = ramp((side-.18)/.14)*ramp((.72-side)/.10)*ramp((row-.24)/.14)*ramp((1.04-row)/.15)
    dist = cv2.distanceTransform((mask<.95).astype(np.uint8),cv2.DIST_L2,5)
    apron = ramp((reach-dist)/max(2.,.48*reach))*zone*guard
    return np.maximum(mask,apron).astype(np.float32)


class DapaoFaceSwapRegion:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return "face-scene-v15-expression-source"


    CATEGORY = "大炮工具箱/图像"
    FUNCTION = "prepare"
    RETURN_TYPES = ("IMAGE","IMAGE","STRING","MASK","INT","INT","INT","INT","INT","INT","IMAGE","IMAGE","DAPAO_FACE_SCENE","IMAGE","STRING","MASK","IMAGE")
    RETURN_NAMES = ("局部底图","局部脸图","换脸指令","贴回遮罩","原图X","原图Y","贴回宽","贴回高","生成宽","生成高","底图选脸预览","脸图选脸预览","底图光影与朝向","原始局部底图","AI看图需求","长发换短发整块贴回遮罩","脸型近景参考")
    @classmethod
    def INPUT_TYPES(cls):
        return {"required":{"底图":("IMAGE",),"脸图":("IMAGE",),"检测器":("BBOX_DETECTOR",),
                "采用脸图完整发型":("BOOLEAN",{"default":False}),
                "眼镜":(["保留底图","跟随脸图","去掉眼镜"],),
                "脸型":(["自然适配","保留底图轮廓","跟随脸图轮廓"],),
                "朝向":(["跟随底图","跟随脸图"],),
                "底图人脸编号":("INT",{"default":0,"min":0,"max":100}),
                "脸图人脸编号":("INT",{"default":0,"min":0,"max":100}),
                "取景外扩":("FLOAT",{"default":.35,"min":.1,"max":1.5,"step":.05}),
                "边缘柔和度":("FLOAT",{"default":.035,"min":.005,"max":.12,"step":.005}),
                "补充要求":("STRING",{"multiline":True,"default":""})},
                "optional":{"底图手工遮罩":("MASK",),"脸图手工遮罩":("MASK",),"五官相似度":(["标准","优先参考脸"] + [str(value) for value in range(1, 100)],),"口罩":(["保留底图","跟随脸图","去掉口罩"],),"脸图表情强度":("INT",{"default":0,"min":0,"max":100}), **{key:(["保留底图","跟随脸图","去掉"],) for key in ("帽子","头饰","耳饰","颈饰")},"旧发丝清理":("INT",{"default":0,"min":0,"max":100}),"肤色基调":(["贴合底图","自然折中","保留脸图"],),"发丝边缘":(["忠于脸图","收至耳后"],),**{k:(["自然适配","保留底图","跟随脸图","去掉"],) for k in ("胡须","妆容彩绘","面部饰件")},"脸型参考强度":("INT",{"default":70,"min":0,"max":100,"display":"slider"})}}

    def prepare(self, 底图, 脸图, 检测器, 采用脸图完整发型, 眼镜, 脸型, 朝向, 底图人脸编号, 脸图人脸编号, 取景外扩, 边缘柔和度, 补充要求, 底图手工遮罩=None, 脸图手工遮罩=None, 五官相似度="标准", 口罩="保留底图", 脸图表情强度=0, 帽子="保留底图", 头饰="保留底图", 耳饰="保留底图", 颈饰="保留底图", 旧发丝清理=0, 肤色基调="贴合底图", 发丝边缘="忠于脸图", 胡须="自然适配", 妆容彩绘="自然适配", 面部饰件="自然适配", 脸型参考强度=70):
        strength = 0.0 if 五官相似度 == "标准" else 1.0 if 五官相似度 == "优先参考脸" else float(五官相似度) / 100
        hair = 采用脸图完整发型
        base = analyze(底图, 检测器, 底图人脸编号, 底图手工遮罩,"底图",hair)
        ref = analyze(脸图, 检测器, 脸图人脸编号, 脸图手工遮罩,"脸图",hair)
        def extent(part):
            if part["manual"] is not None:
                return part["manual"].astype(np.uint8)
            if hair:
                return part["face"] | part["hair"]
            return part["face"].copy()
        mask, reference = extent(base), extent(ref)
        if hair and ref["manual"] is None:
            reference |= ref["scalp"]
        bx,by,br,bb=base["bounds"]
        rx,ry,rr,rb=ref["bounds"]
        face_width=max(1,br-bx)
        sx,sy=face_width/max(1,rr-rx),(bb-by)/max(1,rb-ry)
        transform=np.float32([[sx,0,bx-rx*sx],[0,sy,by-ry*sy]])
        model_base=base["rgb"]
        if hair or 帽子 != "保留底图":
            model_base, guide_area = hair_guide(base, ref, transform, hair, 帽子, 旧发丝清理)
            if base["manual"] is None:
                mask |= guide_area
        accessories={"帽子":帽子,"头饰":头饰,"耳饰":耳饰,"颈饰":颈饰}
        for kind,mode in accessories.items():
            if mode == "保留底图":
                continue
            target_area=accessory_area(base,kind)
            if mode == "跟随脸图":
                donor_area=accessory_area(ref,kind)
                # Small studs and chains occupy very few pixels in the full
                # reference. Give the generator a local cue at the chosen face.
                if kind in ("耳饰","颈饰"):
                    h,w=mask.shape
                    warped=cv2.warpAffine(ref["rgb"],transform,(w,h))
                    area=cv2.warpAffine(donor_area,transform,(w,h))
                    area=cv2.GaussianBlur(area.astype(np.float32),(0,0),max(1,.045*face_width))
                    low=cv2.GaussianBlur(warped,(0,0),max(1,.035*face_width))
                    contrast=np.max(np.abs(warped-low),axis=2)
                    weight=(area*np.clip((contrast-.035)*7,0,.9))[:,:,None]
                    model_base=model_base*(1-weight)+warped*weight

                if ref["manual"] is None:
                    reference |= donor_area
                target_area=target_area | cv2.warpAffine(donor_area,transform,(mask.shape[1],mask.shape[0]),flags=cv2.INTER_NEAREST)
            if base["manual"] is None:
                mask |= target_area
        if base["manual"] is None:
            radius=round(face_width*{"保留底图轮廓":-.025,"自然适配":.04,"跟随脸图轮廓":.12}[脸型])
            if 朝向=="跟随脸图":radius=max(radius,round(face_width*.10))
            kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*abs(radius)+1,)*2)
            mask = cv2.erode(mask,kernel) if radius<0 else cv2.dilate(mask,kernel)
            if not hair and 帽子 == 头饰 == 耳饰 == "保留底图":mask[base["hair"]>0]=0
        # Include fabric and straps which a skin parser may leave outside the crop.
        if 口罩 != "保留底图" and base["manual"] is None:
            mask |= lower_face_region(base)
        if 口罩 == "跟随脸图" and ref["manual"] is None:
            reference |= lower_face_region(ref)
        # Include the lower jaw and immediately below it when explicitly
        # editing a beard; a hidden chin cannot be recovered from a single view.
        if 胡须 in ("跟随脸图","去掉"):
            def beard_area(part):
                l,t,ri,bot=part["bounds"];w,h=ri-l,bot-t
                area=np.zeros_like(part["face"])
                cv2.ellipse(area,(round((l+ri)/2),round(bot-.10*h)),(max(1,round(.53*w)),max(1,round(.48*h))),0,0,360,1,-1)
                return area
            if base["manual"] is None:mask |= beard_area(base)
            if 胡须=="跟随脸图" and ref["manual"] is None:reference |= beard_area(ref)
        if not mask.any() or not reference.any():
            raise ValueError("有效选区为空，请检查人脸编号或手工遮罩")
        padding=max(8,round(取景外扩*face_width))
        feather=max(1,round(face_width*边缘柔和度))
        x,y,r,b=pad_box(box(mask),base["rgb"].shape,max(padding,feather*3+2))
        a,d,c,e=pad_box(box(reference),ref["rgb"].shape,max(8,round((rr-rx)*取景外扩)))
        alpha=cv2.GaussianBlur(mask[y:b,x:r].astype(np.float32),(2*feather+1,)*2,max(.5,feather/2))
        # Keep conditioning independent from output compositing. The workflow
        # can compare these masks on the very same decoded patch.
        ordinary = alpha
        alpha = np.ones_like(ordinary)
        if strength > 0 and 脸型 == "保留底图轮廓" and 口罩 == "保留底图":
            # Keep a narrow band along the original lower cheek and jaw, even
            # when the independently selected hairstyle expands the edit mask.
            face = base["face"][y:b, x:r].astype(np.uint8)
            inside = cv2.distanceTransform(face, cv2.DIST_L2, 3)
            outside = cv2.distanceTransform(1-face, cv2.DIST_L2, 3)
            distance = np.maximum(inside, outside)
            edge = np.clip(distance / max(2, face_width*.055), 0, 1)
            row = np.arange(y,b,dtype=np.float32)[:,None]
            lower = np.clip((row-(by+.48*(bb-by))) / max(1,.18*(bb-by)),0,1)
            alpha *= 1 - strength*lower*(1-edge)
        if 帽子=="保留底图":alpha[base["hat"][y:b,x:r]>0]=0
        # Generate eyewear with the new face. A hard hole here used to copy
        # isolated pieces of the original lens reflection onto the new pupil.
        if base["manual"] is not None:alpha*=base["manual"][y:b,x:r]
        for left,top,right,bottom in base["others"]:
            alpha[max(0,top-y):max(0,bottom-y),max(0,left-x):max(0,right-x)] = 0
        protect = alpha
        alpha = np.rint(ordinary * protect * 255).astype(np.float32) / 255
        wide = alpha
        broad_edit = hair or 帽子!="保留底图" or 头饰!="保留底图" or 颈饰!="保留底图" or 胡须 in ("跟随脸图","去掉")
        if broad_edit and base["manual"] is None and not base["others"]:
            # At an internal crop edge fade back to the original. At a real
            # image edge no seam exists and restoring the old hair is unwanted.
            hh,ww=ordinary.shape
            rows,cols=np.ogrid[:hh,:ww]
            margin=max(2,min(max(feather*2,round(.04*face_width)),max(2,min(hh,ww)//4)))
            edge=np.ones_like(ordinary)
            for internal,distance in ((x>0,cols),(r<base["rgb"].shape[1],ww-1-cols),
                                      (y>0,rows),(b<base["rgb"].shape[0],hh-1-rows)):
                if internal:np.minimum(edge,distance/margin,out=edge)
            edge=edge*edge*(3-2*edge)
            if not hair and 帽子==头饰=="保留底图":
                edge[base["hair"][y:b,x:r]>0]=0
            wide=np.rint(np.maximum(ordinary,edge)*protect*255).astype(np.float32)/255
        base_crop = model_base[y:b,x:r]
        softness=max(strength,脸图表情强度/100)
        if softness > 0:
            base_crop = soften_inner_face(base_crop, base, x, y, alpha, softness)
        cover_text=face_cover_instruction(口罩,base,ref)
        if 脸图表情强度:
            ref_covered="必须佩戴" in face_cover_instruction("跟随脸图",base,ref)
            eye_cues=眼镜=="跟随脸图" or not has_eyewear(ref)
            base_crop=expression_guide(base_crop, ref, base, transform, x, y, alpha,
                                       脸图表情强度/100 * (.60 if 朝向=="跟随底图" else 1.), not ref_covered and "必须佩戴" not in cover_text, eye_cues, 朝向=="跟随底图")
        if 眼镜 == "保留底图" and (base["glasses"].any() or has_eyewear(base)):
            # Keep bilateral frame/bridge cues in the model input when other
            # guides blur or replace the eyes. Never paste these pixels back.
            yy, xx = np.ogrid[y:b,x:r]
            dx = (xx - (bx + br)/2) / max(1, .60*face_width)
            dy = (yy - (by + .42*(bb-by))) / max(1, .26*(bb-by))
            keep = np.clip((1.30-dx*dx-dy*dy)*3,0,1).astype(np.float32)[:,:,None]
            base_crop = base_crop*(1-keep) + base["rgb"][y:b,x:r]*keep
        expression_fraction=脸图表情强度/100
        base_action=""
        shape_source=ref
        if expression_fraction<1:
            base_visible=("必须佩戴" not in cover_text and
                          (口罩=="保留底图" or "必须佩戴" not in face_cover_instruction("保留底图",base,ref)))
            mouth,eyes,base_action=expression_masks(base,base_crop,x,y)
            if not base_visible:
                mouth*=0
                base_action=""
            # A glasses removal request must not reintroduce base frames.
            if 眼镜!="保留底图" and has_eyewear(base):eyes*=0
            action_weight=(np.maximum(mouth,.52*eyes)*alpha*(1-expression_fraction)**2)[:,:,None]
            if 脸型=="跟随脸图轮廓" and 脸型参考强度 and base_visible and "必须佩戴" not in face_cover_instruction("跟随脸图",base,ref):
                # Only suppress mouth action in the redundant contour close-up.
                # The main identity reference remains the original photograph.
                region=ref["rgb"][ry:rb,rx:rr]
                lip,_,_=expression_masks(ref,region,rx,ry)
                wt=(lip*(1-expression_fraction)**2)[:,:,None]
                shape_rgb=ref["rgb"].copy()
                shape_rgb[ry:rb,rx:rr]=region+wt*(cv2.GaussianBlur(region,(0,0),max(2,(rr-rx)*.14))-region)
                shape_source={**ref,"rgb":shape_rgb}
        shape_reference = None
        shape_text = {
            "保留底图轮廓":"保持图1原有脸型与下颌外缘，只替换内侧五官。",
            "自然适配":"参考图2实际可见的脸型，在图1的头身比例和拍摄角度下自然融合。",
        }.get(脸型)
        if 脸型 == "跟随脸图轮廓":
            from .dapao_face_outline import model_reference, model_instruction, soften_target_outline
            shape_reference = model_reference(shape_source, 脸型参考强度)
            shape_text = model_instruction(脸型参考强度)
            if 脸型参考强度 and "必须佩戴" not in cover_text:
                base_crop = soften_target_outline(base_crop,base,(x,y),alpha,脸型参考强度)
        if expression_fraction<1:
            base_crop=base_crop+action_weight*(base["rgb"][y:b,x:r]-base_crop)
        target=sized(base_crop,1024**2)
        donor=sized(ref["rgb"][d:e,a:c],1024**2)
        clauses=["编辑图1中选定的人脸，以图2为身份参考，使眉眼、鼻唇等五官清晰可辨。保留图1的身体姿态、视线、头部尺度、环境光和颈肩衔接。",
                 "以图2实际可见的发际线、分缝、束散方式、发量和发尾位置重建发型；脸侧仅保留属于该发型的发束。" if hair else "严格保留图1发型、发际线和发色。",
                 eyewear_instruction(眼镜, base, ref),
                 shape_text,
                 "头部旋转角度跟随"+("图1。" if 朝向=="跟随底图" else "图2，视线自然适配。")]
        if 朝向 == "跟随底图":
            clauses.insert(0,"头颈姿态以图1拍摄机位为准，保持图1鼻尖相对双眼的横向偏移、远侧脸颊可见宽度和下巴俯仰。")
        clauses.append("把新五官和头皮放在图1现场光源下，额头与两颊的亮面、鼻影方向、下颌投影及肤色色温与图1耳颈自然连续。")
        if strength > 0:
            clauses.append("以图2为唯一五官身份参考，复现眼形和眼距、鼻翼宽度、唇形与五官间距，根据指定头部朝向呈现这些特征。")
        if hair and ref["scalp"].any():
            clauses.insert(0,"按图2复现头顶部露出的头皮范围、发际线后退程度及两侧实际剩余的头发，移除图1厚发和刘海。额头到头顶为连续自然肤色，补全头外背景。")
        if hair and base["hair"].any() and ref["hair"].any():
            old_end = (box(base["hair"])[3]-bb)/max(1,bb-by)
            new_end = (box(ref["hair"])[3]-rb)/max(1,rb-ry)
            if old_end-new_end > .45:
                clauses.insert(0,"首要编辑：去掉图1所有超出图2发尾长度的披散旧发，包括肩上、胸前和两侧散发。根据相邻衣服和背景补画被长发遮住的衣领、肩线、织物纹理和场景。发尾停在图2对应的位置。")
            elif new_end-old_end > .45:
                clauses.insert(0,"按图2延长可见发束，发尾和发量以图2为准，在图1肩颈前后形成自然遮挡，衔接原场景光。")
        if hair and 旧发丝清理 > 0:
            clauses.append("在新发型以外清除底图残留的旧发和旧轮廓，只重建原来被它们挡住的位置。沿相邻边缘延续背景、耳颈或衣料；太阳穴到下颌只留一条自然脸缘，保留新发型自身的细发及选定的配饰。")
        if 脸图表情强度:
            level = "轻微借用" if 脸图表情强度<35 else "融合" if 脸图表情强度<75 else "准确复现"
            clauses.append(level+"图2人物可见的表情，包括眉峰、眼睑开合、脸颊张力、嘴角方向和露齿状态；口罩遮住的嘴部不显示。")
        else:
            lock=("表情完全来自图1：按图1的唇缝、嘴角方向、眼睑开合重画图2身份；嘴的开合与牙齿可见程度以图1为准，图2及脸型近景均不提供表情。")
            if base_action:lock+="图1"+base_action
            clauses.insert(0,lock)
        for kind,mode in accessories.items():
            origin="图1" if mode=="保留底图" else "图2"
            if kind == "头饰" and mode == "跟随脸图":
                clauses.append("发箍、发带、发夹、头巾按图2逐件核对；图2未戴的图1旧头饰全部移除，沿周围头发补全纹理和分缝，即使保留图1发型也照此执行。")
            elif mode=="去掉":
                clauses.append("移除"+kind+"。")
            else:
                clauses.append(kind+"佩戴状态及款式取自"+origin+"，未佩戴则保持空白。")
        tone = {"贴合底图":"", "自然折中":"综合图2面部可见肤色基调与图1耳颈，使下颌色调平滑过渡。", "保留脸图":"保留图2皮肤固有深浅、底色和自然纹理，置于图1现场光。别把两图曝光或妆容差当固有肤色差。下颌向图1耳颈过渡，不给身体全局换色。"}[肤色基调]
        if tone:clauses.append(tone)
        if hair and 发丝边缘=="收至耳后":clauses.append("将可收起的脸颊外散发顺向耳后，清空下颌外侧悬垂的鬓发，忠实保留主发型的编结、卷度或发量，露出的背景接续图1。")
        for name,mode in (("胡须",胡须),("妆容彩绘",妆容彩绘),("面部饰件",面部饰件)):
            if mode=="自然适配":continue
            item={"胡须":"胡须、鬓须及胡茬的覆盖范围和质地","妆容彩绘":"眼妆、唇妆和面部彩绘","面部饰件":"可见鼻环、眉钉、唇钉与面贴（不包含眼镜、耳饰和口罩）"}[name]
            if mode=="去掉":clauses.append("去掉"+item+"，在露出的位置还原自然皮肤和面部结构。")
            else:clauses.append(item+"取自"+("图1" if mode=="保留底图" else "图2")+"，所选人物没有的不要添加；按当前朝向和遮挡呈现。")
        clauses.append(cover_text)
        if 补充要求.strip():clauses.append("在上述设置范围内，"+补充要求.strip())
        rules = "head_swap: " + "".join(clauses)
        brief = (rules + "\n控制面板：脸图表情占比 " + str(脸图表情强度) + "%，脸型" + 脸型 + "，朝向" + 朝向
                 + "。肤色参照：" + (skin_color_hint(base) if 肤色基调=="贴合底图" else tone))
        brief += "。脸型参考强度 " + str(脸型参考强度) + "/100。" if 脸型=="跟随脸图轮廓" else ""
        brief += "。眼周外观来源：" + 眼镜 + "。"
        if hair:
            brief += "按两图实际可见的发型差异，先写目标轮廓、应消失的旧发具体在哪、露出什么；长度近似仍要比较束散和脸侧留发。旧发丝清理强度为" + str(旧发丝清理) + "/100；零表示不额外扫除外围细丝。保持新发本身，不把底图另一人物或背景边线当头发。"
        else:
            brief += "图1只提供头发长度、卷直和分缝。发带、发箍属于头饰，帽子单独执行面板来源。所选来源缺少该物件就清除旧件并补全其下头发。"
        # Expand only the final automatic paste, never the conditioning image,
        # brush limits, or another person's pixels. Do not repaint accessories.
        if not hair and base["manual"] is None and not base["others"] and 脸型=="跟随脸图轮廓" and 脸型参考强度>0:
            allowed = (base["hair"] | base["face"] | base["background"])[y:b,x:r]
            guard = protect * allowed
            bounds = (bx-x,by-y,br-x,bb-y)
            alpha = cheek_paste_margin(alpha,guard,bounds,脸型参考强度)
            wide = np.maximum(wide,alpha)
        return (target,donor,rules,torch.from_numpy(alpha)[None],x,y,r-x,b-y,target.shape[2],target.shape[1],base["preview"],ref["preview"],
                (base["rgb"][y:b,x:r],(bx-x,by-y,br-x,bb-y),朝向=="跟随底图") + (() if 肤色基调=="贴合底图" else (肤色基调,)),
                torch.from_numpy(base["rgb"][y:b,x:r])[None],brief,torch.from_numpy(wide)[None],shape_reference)

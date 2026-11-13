"""Match a generated head patch to the lighting and head pose of the selected base face."""
from functools import lru_cache
from pathlib import Path

import cv2
import folder_paths
import numpy as np
import torch

from .dapao_face_swap_region import parse_parts


@lru_cache(maxsize=1)
def landmark_session():
    import onnxruntime as ort

    path = Path(folder_paths.models_dir) / "insightface/models/buffalo_l/1k3d68.onnx"
    if not path.is_file():
        raise ValueError(f"朝向校正需要 {path}，或将朝向校正设为 0。")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    return ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])


def face_landmarks(rgb, bounds):
    """InsightFace 1k3d68: RGB 0..255, square 1.5x ROI, final 68 XYZ triples."""
    x, y, r, b = bounds
    session = landmark_session()
    size = session.get_inputs()[0].shape[2]
    scale = size / (1.5 * max(r-x, b-y))
    origin = np.array([(x+r)/2, (y+b)/2])
    matrix = np.float32([[scale, 0, size/2-scale*origin[0]], [0, scale, size/2-scale*origin[1]]])
    patch = cv2.warpAffine(rgb[:,:,:3], matrix, (size, size))
    pred = session.run(None, {session.get_inputs()[0].name: (255*patch).transpose(2,0,1)[None]})[0]
    points = pred.reshape(-1,3)[-68:].astype(np.float64) * (size/2 / scale)
    points[:, :2] += origin
    return points


def anchor_pose(rgb, base, bounds, strength):
    """Rotate the generated 3D landmarks; leave identity shape and mouth opening intact."""
    from scipy.interpolate import RBFInterpolator

    a, b = face_landmarks(rgb, bounds), face_landmarks(base, bounds)
    x, y, r, bottom = bounds
    span = max(r-x, bottom-y)
    # Reject implausible estimates (profiles, occlusion, very small manual selections).
    if span < 32 or any(not (.13*span < np.linalg.norm(p[36,:2]-p[45,:2]) < span) for p in (a,b)):
        return rgb
    stable = [0, 4, 8, 12, 16, 27, 28, 29, 30, 31, 35, 36, 39, 42, 45]
    aa, bb = a[stable], b[stable]
    u, _, vt = np.linalg.svd((aa-aa.mean(0)).T @ (bb-bb.mean(0)))
    u[:, -1] *= np.linalg.det(u @ vt)
    rot = u @ vt
    # A single view has no texture behind the far eye or cheek. Only correct
    # small residual rotations; a larger turn belongs in the generation stage.
    axis, _ = cv2.Rodrigues(rot)
    magnitude = np.linalg.norm(axis)
    if magnitude > np.deg2rad(8):
        rot, _ = cv2.Rodrigues(axis * (np.deg2rad(8) / magnitude))
    pivot = (a[39]+a[42])/2
    goal = ((a-pivot) @ rot + pivot)[:,:2]
    center_shift = (b[39,:2]+b[42,:2])/2-pivot[:2]
    delta = (goal-a[:,:2] + np.clip(center_shift, -.025*span, .025*span)) * strength
    biggest = np.linalg.norm(delta, axis=1).max()
    if biggest < .8:
        return rgb
    delta *= min(1., .045*span/biggest)
    # Sparse inverse displacement with stationary anchors outside the skull.
    selected = [0,2,4,6,8,10,12,14,16,17,19,21,22,24,26,27,30,31,35,36,39,42,45,48,51,54,57]
    targets = (a[selected,:2] + delta[selected])/span
    center = np.array([(x+r)/2, (y+bottom)/2])/span
    theta = np.arange(16) * (2*np.pi/16)
    anchors = center + np.column_stack([np.cos(theta)*.85,np.sin(theta)*1.02])
    interpolation = RBFInterpolator(np.vstack([targets,anchors]),
        np.vstack([-delta[selected],np.zeros((len(anchors),2))]), smoothing=.018)
    h,w = rgb.shape[:2]
    # Keep image borders and the plate beyond the head exactly stationary.
    gy,gx = np.meshgrid(np.linspace(0,h-1,max(3,h//8)), np.linspace(0,w-1,max(3,w//8)), indexing="ij")
    coords = np.column_stack([gx.ravel(),gy.ravel()])/span
    offset = interpolation(coords).reshape(*gx.shape,2)
    radius = np.hypot((coords[:,0]-center[0])/.85,(coords[:,1]-center[1])/1.02)
    offset *= np.clip((1-radius)/.18,0,1).reshape(*gx.shape,1)
    offset = cv2.resize(offset.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
    yy,xx = np.indices((h,w),dtype=np.float32)
    return cv2.remap(rgb,xx+offset[:,:,0],yy+offset[:,:,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)


def skin_light(rgb, base, bounds, color, light, match_tone=1.):
    """Estimate smooth lighting differences on shared skin in the original scene."""
    h,w = rgb.shape[:2]
    scale = min(1., 400/max(h,w))
    size = (max(1,round(w*scale)),max(1,round(h*scale)))
    src, dst = [cv2.resize(im,size,interpolation=cv2.INTER_AREA) for im in (rgb,base)]
    parts, original = parse_parts(src), parse_parts(dst)
    lab, ref = [cv2.cvtColor(im,cv2.COLOR_RGB2LAB) for im in (src,dst)]
    x,y,r,b = np.array(bounds)*scale
    fw,fh = max(1,r-x),max(1,b-y)
    yy,xx = np.indices(parts.shape)
    head = ((xx-(x+r)/2)/(.77*fw))**2 + ((yy-(y+.27*fh))/(1.0*fh))**2 < 1
    # Exclude near-neutral mask fabric, saturated lips, pupils and specular pixels
    # from the estimate. Leave pores, wrinkles and other fine detail in the output.
    def sample(image_lab, labels):
        l,a,b = cv2.split(image_lab)
        return (labels==11) & (l>10) & (l<97) & (a>-3) & (a<42) & (np.hypot(a,b)>6)
    valid = head & sample(lab,parts) & sample(ref,original)
    if valid.sum() < max(24,.025*fw*fh):
        return rgb
    diff = ref-lab
    median = np.median(diff[valid], axis=0)
    diff = np.clip(diff, median-[16,8,8],median+[16,8,8]).astype(np.float32)
    sigma = max(2, .14*fw)
    count = cv2.GaussianBlur(valid.astype(np.float32),(0,0),sigma)
    local = cv2.GaussianBlur(diff*valid[:,:,None],(0,0),sigma)
    # Elsewhere (e.g. newly exposed scalp) use a robust global skin offset.
    field = (local+.05*median)/(count[:,:,None]+.05)
    # Match direction/contrast separately from the global exposure and cast.
    # The source mode preserves the generated donor tone; it does not estimate
    # intrinsic skin reflectance or recolour the target body.
    if match_tone != 1.:
        field[:,:,0] -= (1.-match_tone)*median[0]
        color *= match_tone
    field = np.clip(field, [-25,-17,-17],[25,17,17]) * np.float32([light,color,color])
    # Under cool scene light skin itself can be nearly neutral. Classifier
    # islands on a bald crown should not create uncorrected coloured spots.
    # Do not flatten strongly differing skin tones into opaque light patches.
    # Cap the global shift, retaining some local variation from the scene light.
    if abs(median[0])>15:
        field[:,:,0]=13*np.tanh(field[:,:,0]/13)
    radius = max(1,round(fw*.045))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,)*2)
    closed = cv2.morphologyEx((parts==11).astype(np.uint8),cv2.MORPH_CLOSE,disk)
    # A skin-coloured island enclosed by scalp is sometimes labelled as
    # clothing. Fill internal apparel holes above the brows, never exterior hair.
    padded = np.pad(closed,1,constant_values=0)
    cv2.floodFill(padded,None,(0,0),2)
    islands = (padded[1:-1,1:-1]==0) & (yy<y+.34*fh) & (parts==4)
    closed[islands] = 1
    skin = cv2.GaussianBlur((closed*head).astype(np.float32),(0,0),max(1,.035*fw))
    # Transition back to the original scene at the jaw; never apply the face
    # offset uniformly to the unedited neck below it.
    skin *= np.clip((y+1.05*fh-yy)/(.20*fh),0,1)
    field[:,:,1:] = .18*field[:,:,1:] + .82*np.clip(median[1:],-17,17)*color
    # Taper the delta on neutral or dark features to protect glasses, fabric and eyes.
    # Keep broad fabric neutral, with a gradual transition at skin edges.
    coverage = np.clip(lab[:,:,0]/16,0,1)
    neutral = (np.hypot(lab[:,:,1],lab[:,:,2])<5) & (lab[:,:,0]>65)
    fabric = cv2.morphologyEx(neutral.astype(np.uint8),cv2.MORPH_OPEN,disk)
    coverage *= 1-.8*cv2.GaussianBlur(fabric.astype(np.float32),(0,0),max(1,.03*fw))
    delta = cv2.resize((field*(skin*coverage)[:,:,None]).astype(np.float32),(w,h))
    adjusted = cv2.cvtColor(cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)+delta,cv2.COLOR_LAB2RGB)
    return np.where(np.abs(delta).max(2)[:,:,None]>.015,adjusted,rgb)


def neck_seam(rgb, base, bounds, alpha, strength):
    """Match low frequencies on shared neck/shoulder skin inside the real paste boundary."""
    if strength<=0 or alpha.shape!=base.shape[:2]:return rgb
    H,W=alpha.shape
    scale=min(1.,480/max(H,W))
    dims=(max(1,round(W*scale)),max(1,round(H*scale)))
    a=cv2.resize(alpha.astype(np.float32),dims,interpolation=cv2.INTER_AREA)
    if a.min()>.5 or a.max()<=.5:return rgb
    x,y,r,b=np.array(bounds)*scale;fw=max(r-x,1);fh=max(b-y,1)
    yy,xx=np.indices(a.shape)
    roi=(yy>b-.18*fh)&(np.abs(xx-(x+r)/2)<1.65*fw)
    patch,bg=[cv2.resize(im,dims,interpolation=cv2.INTER_AREA) for im in (rgb,base)]
    labs=[cv2.cvtColor(im,cv2.COLOR_RGB2LAB) for im in (patch,bg)]
    fg,old=labs
    valid=roi & (parse_parts(patch)==11) & (parse_parts(bg)==11)
    if valid.sum()<48:return rgb
    d=cv2.distanceTransform((a>.5).astype(np.uint8),cv2.DIST_L2,5)
    band=max(6,.52*fh)
    t=np.clip(1-d/band,0,1)
    t=t*t*(3-2*t)*np.clip((yy-(b-.18*fh))/(.24*fh),0,1)
    sigma=max(1,.065*fw)
    count=cv2.GaussianBlur(valid.astype(np.float32),(0,0),sigma)
    field=cv2.GaussianBlur((old-fg)*valid[:,:,None],(0,0),sigma)/np.maximum(count[:,:,None],.02)
    delta=np.clip(field,[-45,-20,-20],[45,20,20])*(t*valid*strength)[:,:,None]
    delta=cv2.resize(cv2.GaussianBlur(delta.astype(np.float32),(0,0),max(1,.013*fw)),(W,H))
    out=cv2.cvtColor(cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)+delta,cv2.COLOR_LAB2RGB)
    return np.where(np.abs(delta).max(2)[:,:,None]>.05,out,rgb)


class DapaoFaceHarmonize:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return "face-harmonize-model-v5"

    CATEGORY = "大炮工具箱/图像"
    FUNCTION = "run"
    RETURN_TYPES = ("IMAGE",)

    @classmethod
    def INPUT_TYPES(cls):
        def slider(default):
            return ("INT", {"default":default,"min":0,"max":100,"display":"slider"})
        return {"required":{"局部成图":("IMAGE",),"底图依据":("DAPAO_FACE_SCENE",),
            "肤色融合":slider(90),"明暗融合":slider(80),"朝向校正":slider(90)},"optional":{"贴回范围":("MASK",),"颈肩接缝融合":slider(85)}}

    def run(self, 局部成图, 底图依据, 肤色融合, 明暗融合, 朝向校正, 贴回范围=None, 颈肩接缝融合=85, 脸型轮廓校正=70):
        base,bounds,follow,*extra = 底图依据
        match_tone={"自然折中":.5,"保留脸图":0.}.get(extra[0] if extra else None,1.)
        if tuple(局部成图.shape[1:3]) != base.shape[:2]:
            raise ValueError("请先将局部成图缩放至贴回宽高。")
        if not (肤色融合 or 明暗融合 or (follow and 朝向校正) or (贴回范围 is not None and 颈肩接缝融合)):
            return (局部成图,)
        frames = []
        for tensor in 局部成图:
            rgb = tensor.detach().cpu().numpy().astype(np.float32,copy=False)
            if follow and 朝向校正:
                rgb = anchor_pose(rgb,base,bounds,朝向校正/100)
            if 肤色融合 or 明暗融合:
                adjusted = skin_light(rgb[:,:,:3],base,bounds,肤色融合/100,明暗融合/100,match_tone)
                rgb = np.concatenate((adjusted,rgb[:,:,3:]),axis=2) if rgb.shape[2]>3 else adjusted
            if 贴回范围 is not None and 颈肩接缝融合:
                mask=贴回范围.reshape(-1,*贴回范围.shape[-2:])[0].detach().cpu().numpy()
                adjusted=neck_seam(rgb[:,:,:3],base,bounds,mask,颈肩接缝融合/100)
                rgb=np.concatenate((adjusted,rgb[:,:,3:]),axis=2) if rgb.shape[2]>3 else adjusted
            frames.append(torch.from_numpy(rgb))
        return (torch.stack(frames),)

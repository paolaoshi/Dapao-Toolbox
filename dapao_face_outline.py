"""Build an extra photographic reference for Qwen-Image 2.1."""
import cv2
import numpy as np
import torch


def model_reference(face, strength):
    """Square padding preserves photographic proportions even after VAE grid rounding."""
    if strength <= 0:
        return None
    rgb = face["rgb"]
    x, y, right, bottom = face["bounds"]
    height, width = rgb.shape[:2]
    span = max(right-x, bottom-y)
    side = max(32, round(span*1.48))
    left = round((x+right-side)/2)
    top = round((y+bottom-side)/2-.055*span)
    x0,y0 = max(left,0), max(top,0)
    x1,y1 = min(left+side,width), min(top+side,height)
    crop = rgb[y0:y1,x0:x1,:3].copy()
    for l,t,r,b in face["others"]:
        l,t = max(l,x0)-x0,max(t,y0)-y0
        r,b = min(r,x1)-x0,min(b,y1)-y0
        if r>l and b>t:
            crop[t:b,l:r] = np.median(crop,axis=(0,1))
    crop = cv2.copyMakeBorder(crop,y0-top,top+side-y1,x0-left,left+side-x1,
                              cv2.BORDER_REPLICATE)
    # The image encoder keeps native reference resolution when resolution=0.
    # Allocate more image tokens to the real contour as strength increases.
    size = 32*round((160+6.4*strength)/32)
    tile = cv2.resize(crop,(size,size),interpolation=cv2.INTER_AREA if size<=side else cv2.INTER_CUBIC)
    return torch.from_numpy(np.clip(tile,0.,1.).astype(np.float32,copy=False))[None]


def model_instruction(strength):
    if strength <= 0:
        return "保持图1的脸部外轮廓，按图2替换内部五官。"
    degree = ("轻微借用" if strength < 35 else "自然融合" if strength < 75 else "优先忠实复现")
    return (degree+"图2本人可见的脸型。观察额颞宽度、颧部最宽点、面颊饱满度、下颌转折的位置和颏部轮廓；"
            "把整条外缘作为一个连续的立体形状，依选定朝向、表情和现场光重新生成。"
            "头发遮挡与透视缩短按目标机位呈现，只参考可见结构。")

def soften_target_outline(crop, base, origin, edit_mask, strength):
    """Attenuate the old jaw cue only in the conditioning photograph."""
    x,y=origin
    left,top,right,bottom=base["bounds"]
    fw,fh=right-left,bottom-top
    h,w=crop.shape[:2]
    skin=base["face"][y:y+h,x:x+w].astype(np.uint8)
    inside=cv2.distanceTransform(skin,cv2.DIST_L2,3)
    outside=cv2.distanceTransform(1-skin,cv2.DIST_L2,3)
    width=max(3,.19*fw)
    boundary=np.exp(-.5*((inside+outside)/width)**2)
    rows,cols=np.ogrid[y:y+h,x:x+w]
    vertical=np.clip((rows-top-.38*fh)/(.22*fh),0,1)*np.clip((bottom+.30*fh-rows)/(.21*fh),0,1)
    # Protect the central lips; their pose/expression is controlled separately.
    lips=np.exp(-.5*(((cols-(left+right)/2)/max(3,.22*fw))**2+
                       ((rows-top-.71*fh)/max(3,.11*fh))**2))
    amount=(boundary*vertical*(1-lips)*edit_mask*(strength/100.)**1.2).astype(np.float32)
    # A low-frequency copy retains broad scene colours while removing the sharp old outline.
    dims=(max(2,w//4),max(2,h//4))
    low=cv2.resize(crop,dims,interpolation=cv2.INTER_AREA)
    low=cv2.GaussianBlur(low,(0,0),max(1,.20*fw/4))
    return crop+amount[:,:,None]*(cv2.resize(low,(w,h))-crop)

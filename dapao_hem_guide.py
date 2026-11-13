"""Give a lower garment space and a shape cue without stretching the person's body."""
import cv2
import numpy as np
import torch


class DapaoHemGuide:
    CATEGORY = "🍭大炮工具箱/换装"
    FUNCTION = "guide"
    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE")
    RETURN_NAMES = ("人物版型引导", "版型选区", "轮廓预览")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"人物": ("IMAGE",), "原衣": ("MASK",), "手绘": ("MASK",),
                "版型": (["沿用原轮廓", "宽腿裤", "A字裙摆"],),
                "放宽百分比": ("INT", {"default": 40, "min": 0, "max": 90, "step": 5,
                "tooltip": "下摆相对于原衣包围宽度增加的总比例，不是像素；越靠近腰越弱。"})}}

    def guide(self, 人物, 原衣, 手绘, 版型, 放宽百分比):
        manual = bool(手绘.max().item() > 0.02)
        chosen = 手绘 if manual else 原衣
        if 版型 == "沿用原轮廓" or not 放宽百分比 or manual:
            return 人物, chosen, 人物
        if 人物.shape[0] != 1:
            raise ValueError("版型引导每次仅处理一个人物底图。")
        h,w = tuple(人物.shape[1:3])
        m = (chosen.reshape(-1,h,w)[0].detach().cpu().numpy() > .1).astype(np.uint8)
        x,y,bw,bh = cv2.boundingRect(m)
        if bw < 8 or bh < 12:
            raise ValueError("下装选区过小；请检查人物原衣词或手绘。")
        rgb = 人物[0,:,:,:3].detach().cpu().numpy()
        draft = rgb.copy()
        area = m.copy()
        skirt = 版型 == "A字裙摆"
        for v in range(y,y+bh):
            xs = np.flatnonzero(m[v])
            if len(xs) < 4: continue
            progress = (v-y) / max(1,bh-1)
            t = np.clip((progress-(.10 if skirt else .30))/(.90 if skirt else .70),0,1)
            t = t*t*(3-2*t)
            spread = round(.5*bw*(放宽百分比/100)*t)
            if spread == 0: continue
            # Keep separated pant legs separated; flare each leg around its own midline.
            breaks = np.where(np.diff(xs)>max(3,round(bw*.015)))[0]+1
            runs = [run for run in np.split(xs,breaks) if len(run)>=max(3,bw*.035)]
            if not runs: continue
            for j,run in enumerate(runs):
                a,b=int(run[0]),int(run[-1])
                left= max(0,a-(spread if j==0 else min(spread,(a-int(runs[j-1][-1]))//3)))
                right=min(w-1,b+(spread if j==len(runs)-1 else min(spread,(int(runs[j+1][0])-b)//3)))
                dst=np.arange(left,right+1)
                src=np.linspace(a,b,len(dst))
                lo=src.astype(int); hi=np.minimum(lo+1,b)
                valid=m[v,np.rint(src).astype(int)]>0
                frac=(src-lo)[:,None]
                draft[v,dst[valid]]=((1-frac)*rgb[v,lo]+frac*rgb[v,hi])[valid]
                area[v,dst[valid]]=1
            if skirt and progress>.18 and len(runs)>1:
                area[v,int(runs[0][-1]):int(runs[-1][0])+1]=1
        overlay=rgb.copy()
        extra=(area!=0)&(m==0)
        overlay[extra]=overlay[extra]*.48+np.array([0.12,.82,.76])*.52
        for base,color in ((m,(1.,.68,.12)),(area,(.05,.90,.80))):
            contours=cv2.findContours(base,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]
            cv2.drawContours(overlay,contours,-1,color,max(2,round(min(w,h)/400)))
        return (torch.from_numpy(draft)[None].to(人物), torch.from_numpy(area.astype(np.float32))[None].to(原衣),
                torch.from_numpy(overlay)[None].to(人物))

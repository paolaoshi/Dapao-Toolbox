"""Clothing selection and crop geometry; no inference or model loading."""
import numpy as np
import torch
import cv2

ITEMS = {"上装":"shirt,blouse,sweater", "下装":"pants,skirt,shorts", "裤子":"pants", "短裤":"shorts", "裙子":"skirt", "连衣裙":"dress", "外套":"jacket,coat", "披肩":"shawl,cape", "内衣上装":"bra", "内衣下装":"underpants", "内衣套装":"bra,underpants", "泳装":"swimsuit", "帽子":"hat", "鞋子":"shoes", "整套服装":"clothing", "自定义组合":"clothing"}
class OutfitRules:
    CATEGORY="🍭大炮工具箱/换装"
    FUNCTION="run"
    RETURN_TYPES=("STRING","STRING","STRING")
    RETURN_NAMES=("参考图取件","人物图选区","固定换装指令")
    @classmethod
    def INPUT_TYPES(cls):
        s=lambda: ("STRING",{"default":""})
        return {"required":{"换装类别":(list(ITEMS),),"参考取件词":s(),"人物原衣词":s(),"补充要求":("STRING",{"default":"","multiline":True})}}
    def run(self,换装类别,参考取件词,人物原衣词,补充要求):
        ref=参考取件词.strip() or ITEMS[换装类别]
        if 换装类别=="自定义组合" and not 参考取件词.strip(): raise ValueError("自定义组合请填写英文取件词，用英文逗号分隔。")
        target=人物原衣词.strip() or ref
        return ref,target,(f"Edit image 1: dress the same person in the selected {ref} from image 2. Image 2 determines which pieces, silhouette, cut, colors and design to transfer; any later images are close-up details of the same clothing only. Fit the garments to the original pose and anatomy under the original lighting. Keep face, hair, hands, pose, background and unselected garments unchanged. Respect occlusions. Do not transfer the reference model, hanger or background. {补充要求}")

class OutfitRegions:
    CATEGORY="🍭大炮工具箱/换装"
    FUNCTION="run"
    RETURN_TYPES=("IMAGE","IMAGE","MASK","INT","INT","INT","INT")
    RETURN_NAMES=("人物局部","服装净图","贴回遮罩","左","上","原宽","原高")
    @classmethod
    def INPUT_TYPES(cls):
        return {"required":{**{k:("IMAGE",) for k in ("人物","服装")},**{k:("MASK",) for k in ("人物自动","服装自动","人物手绘","服装手绘")},"外扩像素":("INT",{"default":12,"min":0,"max":160}),"羽化像素":("INT",{"default":5,"min":0,"max":64}),"上下文比例":("FLOAT",{"default":0.30,"min":0.05,"max":1.0,"step":0.05})}}
    def run(self,人物,服装,人物自动,服装自动,人物手绘,服装手绘,外扩像素,羽化像素,上下文比例):
        def get(img,auto,manual,label):
            m=manual if manual.max().item()>0.02 else auto
            a=(m.reshape(-1,*m.shape[-2:])[0].detach().cpu().numpy()>0.1).astype(np.uint8)
            if tuple(a.shape)!=tuple(img.shape[1:3]) or not a.any():raise ValueError(label+"未选中有效区域，请调整类别、英文选区词或在该图画遮罩。")
            return a
        def box(a,pad):
            x,y,w,h=cv2.boundingRect(a)
            return max(0,x-pad),max(0,y-pad),min(a.shape[1],x+w+pad),min(a.shape[0],y+h+pad)
        m=get(人物,人物自动,人物手绘,"人物"); r=get(服装,服装自动,服装手绘,"服装")
        if 外扩像素:
            k=2*外扩像素+1
            m=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
        _,_,w,h=cv2.boundingRect(m)
        x,y,X,Y=box(m,max(羽化像素*3,round(max(w,h)*上下文比例)))
        a=m.astype(np.float32)
        if 羽化像素:a=cv2.GaussianBlur(a,(2*羽化像素+1,2*羽化像素+1),max(0.5,羽化像素/2))
        l,t,R,B=box(r,max(4,round(max(cv2.boundingRect(r)[2:])*0.035)))
        alpha=torch.from_numpy(r[t:B,l:R].copy()).to(服装)[None,:,:,None]
        clean=服装[:,t:B,l:R,:3]*alpha+(1-alpha)*0.90
        return 人物[:,y:Y,x:X,:3],clean,torch.from_numpy(a[y:Y,x:X].copy())[None],x,y,X-x,Y-y

NODE_CLASS_MAPPINGS={"DapaoOutfitRules":OutfitRules,"DapaoOutfitRegions":OutfitRegions}
NODE_DISPLAY_NAME_MAPPINGS={"DapaoOutfitRules":"🧥 换装类别与取件@炮老师小课堂","DapaoOutfitRegions":"✂️ 换装局部与贴回范围@炮老师小课堂"}

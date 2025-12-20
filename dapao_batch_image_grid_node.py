import torch
import numpy as np
from PIL import Image
import math

class DapaoBatchImageGrid:
    """
    🐭批次图组合@炮老师的小课堂
    
    功能：
    - 将输入的图像批次按网格排列组合成一张大图
    - 支持灵活的行列设置（优先列数，可指定行数）
    - 支持单图尺寸自定义（0为原图尺寸）
    - 支持间距（Gap）设置
    - 支持多种裁剪/缩放模式
    - 支持背景颜色设置
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "🖼️ 图像批次": ("IMAGE", {"tooltip": "输入的图像批次"}),
                "📊 列数": ("INT", {
                    "default": 3, 
                    "min": 0, 
                    "max": 100, 
                    "step": 1, 
                    "tooltip": "网格列数。设置>0时优先生效；设置为0时使用行数计算"
                }),
                "🧱 行数": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 100, 
                    "step": 1, 
                    "tooltip": "网格行数。当列数为0时生效（自动算列数）；当列数>0时，作为最小行数（不够留白）"
                }),
                "↔️ 单图宽度": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 8192, 
                    "step": 1, 
                    "tooltip": "单张小图宽度。0表示使用原图宽度"
                }),
                "↕️ 单图高度": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 8192, 
                    "step": 1, 
                    "tooltip": "单张小图高度。0表示使用原图高度"
                }),
                "📏 间距": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 512, 
                    "step": 1, 
                    "tooltip": "小图之间的间距（像素）"
                }),
                "✂️ 裁剪模式": (["原比例", "拉伸", "居中裁剪", "顶部裁剪", "底部裁剪", "左侧裁剪", "右侧裁剪"], {
                    "default": "原比例",
                    "tooltip": "当原图与目标尺寸比例不一致时的处理方式"
                }),
                "🎨 背景类型": (["透明", "自定义颜色"], {
                    "default": "透明",
                    "tooltip": "背景填充类型"
                }),
                "🎨 背景颜色": ("STRING", {
                    "default": "#FFFFFF", 
                    "tooltip": "背景颜色（Hex格式，如#FFFFFF），仅在自定义颜色模式下生效"
                }),
                "📏 限制最长边": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 16384, 
                    "step": 64, 
                    "tooltip": "输出图像限制最长边（像素），0为不限制"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("🖼️ 拼接图像",)
    FUNCTION = "create_grid"
    CATEGORY = "🤖Dapao-Toolbox"

    def create_grid(self, **kwargs):
        # 1. 解析输入
        images = kwargs["🖼️ 图像批次"]
        columns = kwargs["📊 列数"]
        rows = kwargs["🧱 行数"]
        width = kwargs["↔️ 单图宽度"]
        height = kwargs["↕️ 单图高度"]
        gap = kwargs["📏 间距"]
        crop_mode = kwargs["✂️ 裁剪模式"]
        bg_type = kwargs["🎨 背景类型"]
        bg_color = kwargs["🎨 背景颜色"]
        max_side = kwargs["📏 限制最长边"]

        if images is None or len(images) == 0:
            raise ValueError("❌ 错误：输入图像批次为空")
            
        batch_size, img_h, img_w, _ = images.shape
        
        # 2. 确定目标尺寸
        target_w = width if width > 0 else img_w
        target_h = height if height > 0 else img_h
        
        # 3. 计算行列布局
        if columns > 0:
            cols = columns
            # 如果指定了rows，取较大值以确保布局（可能是留白）
            # 但必须至少能容纳所有图片：batch_size
            needed_rows = math.ceil(batch_size / cols)
            final_rows = max(rows, needed_rows) if rows > 0 else needed_rows
        elif rows > 0:
            final_rows = rows
            cols = math.ceil(batch_size / final_rows)
        else:
            # 默认 3列
            cols = 3
            final_rows = math.ceil(batch_size / cols)
            
        # 4. 准备画布
        # 宽度 = 列数 * 单图宽 + (列数 - 1) * 间距
        # 高度 = 行数 * 单图高 + (行数 - 1) * 间距
        # 考虑到边缘可能也需要间距？通常 Grid 不包含外边框间距，只包含元素间距。这里按元素间距处理。
        
        canvas_w = cols * target_w + (cols - 1) * gap
        canvas_h = final_rows * target_h + (final_rows - 1) * gap
        
        # 避免 gap 导致负数（当 cols=0 或 1 时 gap 系数为 0）
        canvas_w = max(canvas_w, 1)
        canvas_h = max(canvas_h, 1)

        # 解析背景色
        if bg_type == "透明":
            color = (0, 0, 0, 0)
            mode = "RGBA"
        else:
            try:
                c = bg_color.lstrip('#')
                rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
                color = rgb + (255,)
                mode = "RGBA"
            except:
                color = (255, 255, 255, 255)
                mode = "RGBA"

        canvas = Image.new(mode, (canvas_w, canvas_h), color)
        
        # 5. 逐张处理并粘贴
        for idx, img_tensor in enumerate(images):
            # 超过网格容量的图片将被忽略（如果 rows 限制了总数且 cols 也固定... 但上面的逻辑 needed_rows 保证了能装下）
            # 除非 columns=0, rows>0 且 batch_size > rows*cols? 
            # 比如 rows=2, batch=5 -> cols=3 -> 2*3=6 > 5. OK.
            
            # 计算当前行列
            r = idx // cols
            c = idx % cols
            
            # 如果超出计算出的行数（理论上不会，除非逻辑有误），跳过
            if r >= final_rows:
                break
                
            # Tensor -> PIL
            i = 255. * img_tensor.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # 处理单图 (缩放/裁剪)
            processed_img = self.process_image(img, target_w, target_h, crop_mode)
            
            # 确保是 RGBA 以支持透明背景合成
            if processed_img.mode != "RGBA":
                processed_img = processed_img.convert("RGBA")
                
            # 计算坐标
            x = c * (target_w + gap)
            y = r * (target_h + gap)
            
            # 粘贴 (使用 alpha composite)
            canvas.paste(processed_img, (x, y), processed_img)
            
        # 6. 限制最大边
        if max_side > 0:
            w, h = canvas.size
            if w > max_side or h > max_side:
                ratio = min(max_side / w, max_side / h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                canvas = canvas.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
        # 7. 输出
        # PIL -> Tensor
        img_np = np.array(canvas).astype(np.float32) / 255.0
        output = torch.from_numpy(img_np).unsqueeze(0) # [1, H, W, C]
        
        return (output,)

    def process_image(self, img, target_w, target_h, mode):
        # 如果尺寸完全一致，直接返回
        if img.size == (target_w, target_h):
            return img
            
        if mode == "拉伸":
            return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
        img_w, img_h = img.size
        
        if mode == "原比例":
            # 缩放以适应目标框 (Aspect Fit)
            scale = min(target_w / img_w, target_h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # 创建透明底
            res = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            # 居中粘贴
            x = (target_w - new_w) // 2
            y = (target_h - new_h) // 2
            res.paste(resized, (x, y))
            return res
            
        # 裁剪模式 (Aspect Fill + Crop)
        # 先缩放到覆盖目标区域
        scale = max(target_w / img_w, target_h / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        left, top = 0, 0
        if new_w > target_w:
            if mode in ["居中裁剪", "顶部裁剪", "底部裁剪"]:
                left = (new_w - target_w) // 2
            elif mode == "右侧裁剪":
                left = new_w - target_w
            # 左侧裁剪 left=0
            
        if new_h > target_h:
            if mode in ["居中裁剪", "左侧裁剪", "右侧裁剪"]:
                top = (new_h - target_h) // 2
            elif mode == "底部裁剪":
                top = new_h - target_h
            # 顶部裁剪 top=0
            
        return resized.crop((left, top, left + target_w, top + target_h))

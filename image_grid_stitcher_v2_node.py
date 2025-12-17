import torch
import numpy as np
from PIL import Image, ImageDraw
import math

class ImageGridStitcherV2Node:
    """
    图片网格拼接 V2 - 解决缓存问题的全新版本
    
    功能说明：
    - 接收图像批次
    - 按指定行列数排列
    - 强制统一每张小图的宽高
    - 支持多种裁剪模式（含原比例）
    - 支持自定义背景（透明或颜色）
    - 支持限制输出总尺寸
    """
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 🖼️ 图像批次
                "🖼️ 图像批次": ("IMAGE", {
                    "tooltip": "输入的图像批次，包含多张需要拼接的图片"
                }),
                # 📊 列数
                "📊 列数": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "网格的列数，行数将根据图片数量自动计算"
                }),
                # ↔️ 单图宽度
                "↔️ 单图宽度": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 4096,
                    "step": 8,
                    "tooltip": "每张小图在网格中的强制宽度"
                }),
                # ↕️ 单图高度
                "↕️ 单图高度": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 4096,
                    "step": 8,
                    "tooltip": "每张小图在网格中的强制高度"
                }),
                # ✂️ 裁剪模式
                "✂️ 裁剪模式": (["原比例", "拉伸", "居中裁剪", "顶部裁剪", "底部裁剪", "左侧裁剪", "右侧裁剪"], {
                    "default": "原比例",
                    "tooltip": "当原图比例与目标宽高不一致时的处理方式"
                }),
                # 🎨 背景类型
                "🎨 背景类型": (["透明", "自定义颜色"], {
                    "default": "透明",
                    "tooltip": "拼接背景的填充方式"
                }),
                # 🎨 背景颜色
                "🎨 背景颜色": ("STRING", {
                    "default": "#FFFFFF",
                    "multiline": False,
                    "tooltip": "自定义背景颜色（Hex格式，如#FFFFFF），仅在背景类型为'自定义颜色'时生效"
                }),
                # 📏 限制最长边
                "📏 限制最长边": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 16384,
                    "step": 64,
                    "tooltip": "限制输出大图的最长边像素，0表示不限制"
                }),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("🖼️ 拼接图像",)
    FUNCTION = "stitch_images"
    CATEGORY = "🤖Dapao-Toolbox"
    
    def stitch_images(self, **kwargs):
        # 1. 获取输入参数
        images = kwargs["🖼️ 图像批次"]
        columns = kwargs["📊 列数"]
        cell_w = kwargs["↔️ 单图宽度"]
        cell_h = kwargs["↕️ 单图高度"]
        crop_mode = kwargs["✂️ 裁剪模式"]
        bg_type = kwargs["🎨 背景类型"]
        bg_color_hex = kwargs["🎨 背景颜色"]
        max_side = kwargs["📏 限制最长边"]
        
        # 2. 计算网格行列
        batch_size = images.shape[0]
        if batch_size == 0:
            raise ValueError("❌ 错误: 输入的图像批次为空！")
            
        rows = math.ceil(batch_size / columns)
        
        # 3. 准备画布
        canvas_w = columns * cell_w
        canvas_h = rows * cell_h
        
        # 解析背景颜色
        if bg_type == "透明":
            bg_color = (0, 0, 0, 0)
            mode = "RGBA"
        else:
            # 解析Hex颜色
            try:
                c = bg_color_hex.lstrip('#')
                rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
                bg_color = rgb + (255,) # 添加Alpha通道为不透明
                mode = "RGBA"
            except:
                print(f"Warning: Invalid color code {bg_color_hex}, defaulting to black.")
                bg_color = (0, 0, 0, 255)
                mode = "RGBA"
        
        canvas = Image.new(mode, (canvas_w, canvas_h), bg_color)
        
        # 4. 处理每一张图片
        for idx, img_tensor in enumerate(images):
            # tensor (H, W, C) -> PIL
            # 输入tensor范围是0-1，需要乘以255
            i = 255. * img_tensor.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # 处理尺寸和裁剪
            processed_img = self.process_single_image(img, cell_w, cell_h, crop_mode)
            
            # 计算位置
            col = idx % columns
            row = idx // columns
            x = col * cell_w
            y = row * cell_h
            
            # 粘贴到画布
            if processed_img.mode != 'RGBA':
                processed_img = processed_img.convert('RGBA')
                
            # 修正粘贴逻辑：总是使用alpha混合
            canvas.paste(processed_img, (x, y), processed_img)

        # 5. 整体缩放
        if max_side > 0:
            w, h = canvas.size
            if w > max_side or h > max_side:
                ratio = min(max_side / w, max_side / h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                canvas = canvas.resize((new_w, new_h), Image.LANCZOS)

        # 6. 转回 Tensor
        img_np = np.array(canvas).astype(np.float32) / 255.0
        output = torch.from_numpy(img_np).unsqueeze(0) # (1, H, W, C)
        
        return (output,)

    def process_single_image(self, img, target_w, target_h, mode):
        """处理单张图片的缩放和裁剪"""
        if mode == "拉伸":
            return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # 原比例模式 (Aspect Fit)
        if mode == "原比例":
            img_w, img_h = img.size
            
            # 计算缩放比例，取较小值以保证图片完整放入
            scale_w = target_w / img_w
            scale_h = target_h / img_h
            scale = min(scale_w, scale_h)
            
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            
            # 缩放图片
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # 创建透明底图
            final_img = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            
            # 计算居中位置
            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) // 2
            
            # 粘贴图片（保持透明度）
            final_img.paste(resized_img, (paste_x, paste_y))
            
            return final_img
        
        # 裁剪模式
        img_w, img_h = img.size
        
        # 1. 等比缩放到覆盖目标区域
        scale_w = target_w / img_w
        scale_h = target_h / img_h
        scale = max(scale_w, scale_h) # 取大值以覆盖
        
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 2. 计算裁剪坐标
        left = 0
        top = 0
        
        # 宽度超出或相等
        if new_w > target_w:
            if mode == "居中裁剪" or mode == "顶部裁剪" or mode == "底部裁剪":
                left = (new_w - target_w) // 2
            elif mode == "左侧裁剪":
                left = 0
            elif mode == "右侧裁剪":
                left = new_w - target_w
        
        # 高度超出或相等
        if new_h > target_h:
            if mode == "居中裁剪" or mode == "左侧裁剪" or mode == "右侧裁剪":
                top = (new_h - target_h) // 2
            elif mode == "顶部裁剪":
                top = 0
            elif mode == "底部裁剪":
                top = new_h - target_h
                
        right = left + target_w
        bottom = top + target_h
        
        return resized_img.crop((left, top, right, bottom))

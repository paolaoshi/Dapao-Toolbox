import torch
import numpy as np
from PIL import Image, ImageOps

class ImageAspectRatioResizeNode:
    """
    按宽高比缩放节点
    
    功能说明：
    - 支持多种预设宽高比和自定义比例
    - 支持按边长、最长边、最短边缩放
    - 支持适应(Letterbox)、裁剪(Crop)、拉伸(Stretch)模式
    - 支持遮罩(Mask)同步处理
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "📸 图像": ("IMAGE",),
                "📐 宽高比": (["原图", "自定义", "1:1", "16:9", "4:3", "3:2", "2:3", "9:16", "3:4", "21:9", "9:21"], {
                    "default": "原图",
                    "tooltip": "选择目标宽高比，原图=保持原始比例，自定义=手动设置比例"
                }),
                "📏 比例宽度": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 10000,
                    "step": 1,
                    "tooltip": "自定义宽高比的宽度值（当宽高比选'自定义'时生效）"
                }),
                "📏 比例高度": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 10000,
                    "step": 1,
                    "tooltip": "自定义宽高比的高度值（当宽高比选'自定义'时生效）"
                }),
                "🎨 适应模式": (["包含", "裁剪", "拉伸"], {
                    "default": "包含",
                    "tooltip": "包含=黑边填充(Letterbox), 裁剪=充满画面(Crop), 拉伸=变形充满(Stretch)"
                }),
                "🔍 缩放算法": (["lanczos", "bicubic", "bilinear", "nearest"], {
                    "default": "lanczos",
                    "tooltip": "图像缩放插值算法"
                }),
                "🔢 尺寸倍数": ("INT", {
                    "default": 8,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "tooltip": "确保输出尺寸是该数值的倍数（通常为8）"
                }),
                "📏 锁定边长": (["不锁定", "锁定宽度", "锁定高度", "锁定最长边", "锁定最短边"], {
                    "default": "不锁定",
                    "tooltip": "选择要锁定的边长基准"
                }),
                "📏 锁定长度": ("INT", {
                    "default": 1024,
                    "min": 1,
                    "max": 16384,
                    "step": 1,
                    "tooltip": "锁定边的目标长度像素值"
                }),
                "🌈 背景颜色": ("STRING", {
                    "default": "#000000",
                    "multiline": False,
                    "tooltip": "包含(Letterbox)模式下的填充背景色(Hex格式)"
                })
            },
            "optional": {
                "😷 遮罩": ("MASK",)
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "INT")
    RETURN_NAMES = ("🖼️ 图像", "😷 遮罩", "📏 原始尺寸", "📏 宽度", "📏 高度")
    FUNCTION = "resize_image"
    CATEGORY = "🤖Dapao-Toolbox"

    def resize_image(self, **kwargs):
        # 获取参数 (使用中文键名)
        image = kwargs.get("📸 图像")
        aspect_ratio = kwargs.get("📐 宽高比", "原图")
        proportional_width = kwargs.get("📏 比例宽度", 1)
        proportional_height = kwargs.get("📏 比例高度", 1)
        fit_mode = kwargs.get("🎨 适应模式", "包含")
        method = kwargs.get("🔍 缩放算法", "lanczos")
        round_to_multiple = kwargs.get("🔢 尺寸倍数", 8)
        scale_to_side = kwargs.get("📏 锁定边长", "不锁定")
        scale_to_length = kwargs.get("📏 锁定长度", 1024)
        background_color = kwargs.get("🌈 背景颜色", "#000000")
        mask = kwargs.get("😷 遮罩", None)
        
        # 参数映射
        fit_mode_map = {
            "包含": "letterbox",
            "裁剪": "crop",
            "拉伸": "stretch"
        }
        fit_mode_en = fit_mode_map.get(fit_mode, "letterbox")
        
        scale_to_side_map = {
            "不锁定": "None",
            "锁定宽度": "Width",
            "锁定高度": "Height",
            "锁定最长边": "Longest",
            "锁定最短边": "Shortest"
        }
        scale_to_side_en = scale_to_side_map.get(scale_to_side, "None")
        
        # 转换方法
        method_map = {
            "lanczos": Image.Resampling.LANCZOS,
            "bicubic": Image.Resampling.BICUBIC,
            "bilinear": Image.Resampling.BILINEAR,
            "nearest": Image.Resampling.NEAREST
        }
        resample_method = method_map.get(method, Image.Resampling.LANCZOS)
        
        # 处理 batch
        result_images = []
        result_masks = []
        
        # 确保 image 是 list (batch)
        if len(image.shape) < 4:
            image = image.unsqueeze(0)
            
        batch_size = image.shape[0]
        
        # 处理 mask
        if mask is not None:
            if len(mask.shape) < 3:
                mask = mask.unsqueeze(0)
            # 如果 mask batch 小于 image batch，需要广播
            if mask.shape[0] < batch_size:
                mask = mask.repeat(batch_size, 1, 1)
        
        original_width = 0
        original_height = 0
        final_width = 0
        final_height = 0

        for i in range(batch_size):
            # 1. 转换为 PIL
            img_tensor = image[i]
            img_pil = self.tensor2pil(img_tensor)
            
            w, h = img_pil.size
            original_width = w
            original_height = h
            
            # 2. 计算目标宽高比
            target_ratio = w / h
            if aspect_ratio != "原图":
                if aspect_ratio == "自定义":
                    target_ratio = proportional_width / proportional_height
                else:
                    try:
                        w_ratio, h_ratio = map(float, aspect_ratio.split(":"))
                        target_ratio = w_ratio / h_ratio
                    except:
                        target_ratio = w / h

            # 3. 计算目标尺寸
            target_w = w
            target_h = h
            
            if scale_to_side_en == "None":
                # 不强制指定边长，根据 fit_mode 和宽高比计算
                if fit_mode_en == "letterbox" or fit_mode_en == "stretch":
                    # 包含原图：如果原图较宽，以宽为准；如果原图较高，以高为准
                    # 但这里我们需要得到目标宽高比
                    # Letterbox: 目标框包含原图。
                    # 如果 w/h > target_ratio (原图更宽)，则宽不变，高增加 -> target_w = w, target_h = w / target_ratio
                    # 如果 w/h < target_ratio (原图更高)，则高不变，宽增加 -> target_h = h, target_w = h * target_ratio
                    if w / h > target_ratio:
                        target_w = w
                        target_h = int(w / target_ratio)
                    else:
                        target_h = h
                        target_w = int(h * target_ratio)
                elif fit_mode_en == "crop":
                    # 裁剪原图：目标框在原图内
                    # 如果 w/h > target_ratio (原图更宽)，则高不变，宽减小 -> target_h = h, target_w = h * target_ratio
                    # 如果 w/h < target_ratio (原图更高)，则宽不变，高减小 -> target_w = w, target_h = w / target_ratio
                    if w / h > target_ratio:
                        target_h = h
                        target_w = int(h * target_ratio)
                    else:
                        target_w = w
                        target_h = int(w / target_ratio)
            else:
                # 指定了基准边和长度
                length = scale_to_length
                if scale_to_side_en == "Width":
                    target_w = length
                    target_h = int(length / target_ratio)
                elif scale_to_side_en == "Height":
                    target_h = length
                    target_w = int(length * target_ratio)
                elif scale_to_side_en == "Longest":
                    if target_ratio >= 1: # 宽 >= 高
                        target_w = length
                        target_h = int(length / target_ratio)
                    else:
                        target_h = length
                        target_w = int(length * target_ratio)
                elif scale_to_side_en == "Shortest":
                    if target_ratio >= 1: # 宽 >= 高，高是短边
                        target_h = length
                        target_w = int(length * target_ratio)
                    else: # 宽是短边
                        target_w = length
                        target_h = int(length / target_ratio)
            
            # 4. 四舍五入对齐
            if round_to_multiple > 1:
                target_w = (target_w + round_to_multiple - 1) // round_to_multiple * round_to_multiple
                target_h = (target_h + round_to_multiple - 1) // round_to_multiple * round_to_multiple
            
            final_width = target_w
            final_height = target_h
            
            # 5. 执行缩放处理
            
            # 准备背景颜色
            bg_color_rgb = self.hex_to_rgb(background_color)
            
            # 创建目标画布
            new_img = Image.new("RGB", (target_w, target_h), bg_color_rgb)
            
            # 对应的 mask 画布 (黑色背景)
            new_mask = Image.new("L", (target_w, target_h), 0)
            
            # 获取当前 mask (如果有)
            current_mask = None
            if mask is not None:
                current_mask = self.tensor2pil_mask(mask[i])
            
            if fit_mode_en == "stretch":
                # 拉伸模式：直接缩放到目标尺寸
                resized_img = img_pil.resize((target_w, target_h), resample_method)
                new_img.paste(resized_img, (0, 0))
                
                if current_mask:
                    resized_mask = current_mask.resize((target_w, target_h), resample_method)
                    new_mask.paste(resized_mask, (0, 0))
                else:
                    # 如果没有输入 mask，拉伸模式下默认全白 mask (表示全图有效)
                    new_mask = Image.new("L", (target_w, target_h), 255)
                    
            elif fit_mode_en == "crop":
                # 裁剪模式：先保持比例缩放到覆盖目标尺寸，然后居中裁剪
                # 计算缩放比例：取宽比和高比中较大的那个（保证覆盖）
                scale = max(target_w / w, target_h / h)
                scaled_w = int(w * scale)
                scaled_h = int(h * scale)
                
                resized_img = img_pil.resize((scaled_w, scaled_h), resample_method)
                
                # 计算居中裁剪位置
                left = (scaled_w - target_w) // 2
                top = (scaled_h - target_h) // 2
                
                # Crop
                cropped_img = resized_img.crop((left, top, left + target_w, top + target_h))
                new_img.paste(cropped_img, (0, 0))
                
                if current_mask:
                    resized_mask = current_mask.resize((scaled_w, scaled_h), resample_method)
                    cropped_mask = resized_mask.crop((left, top, left + target_w, top + target_h))
                    new_mask.paste(cropped_mask, (0, 0))
                else:
                    new_mask = Image.new("L", (target_w, target_h), 255)

            else: # letterbox (默认)
                # 适应模式：保持比例缩放到包含在目标尺寸内，居中，填充背景
                # 计算缩放比例：取宽比和高比中较小的那个（保证包含）
                scale = min(target_w / w, target_h / h)
                scaled_w = int(w * scale)
                scaled_h = int(h * scale)
                
                resized_img = img_pil.resize((scaled_w, scaled_h), resample_method)
                
                # 计算居中位置
                left = (target_w - scaled_w) // 2
                top = (target_h - scaled_h) // 2
                
                new_img.paste(resized_img, (left, top))
                
                if current_mask:
                    resized_mask = current_mask.resize((scaled_w, scaled_h), resample_method)
                    new_mask.paste(resized_mask, (left, top))
                else:
                    # 原图区域为白，背景为黑
                    white_block = Image.new("L", (scaled_w, scaled_h), 255)
                    new_mask.paste(white_block, (left, top))
            
            result_images.append(self.pil2tensor(new_img))
            result_masks.append(self.pil2tensor_mask(new_mask))

        # 合并 batch
        final_images_tensor = torch.cat(result_images, dim=0)
        final_masks_tensor = torch.cat(result_masks, dim=0)
        
        # 返回 5 个值，对应 5 个 RETURN_TYPES
        return (final_images_tensor, final_masks_tensor, original_width, final_width, final_height)

    def hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为RGB元组"""
        hex_color = hex_color.lstrip('#')
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (0, 0, 0)

    def tensor2pil(self, image):
        return Image.fromarray(np.clip(255. * image.cpu().numpy(), 0, 255).astype(np.uint8))

    def pil2tensor(self, image):
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)
        
    def tensor2pil_mask(self, mask):
        return Image.fromarray(np.clip(255. * mask.cpu().numpy(), 0, 255).astype(np.uint8), mode='L')

    def pil2tensor_mask(self, mask):
        return torch.from_numpy(np.array(mask).astype(np.float32) / 255.0).unsqueeze(0)

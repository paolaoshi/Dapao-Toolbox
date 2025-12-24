import torch
import numpy as np
import os
from PIL import Image, ImageOps

class DapaoBatchImageResize:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "📊 缩放模式": (["📏 按长边缩放", "📐 按短边缩放", "🔢 强制拉伸至指定尺寸", "✂️ 缩放并裁剪至指定尺寸"], {"default": "✂️ 缩放并裁剪至指定尺寸"}),
                "🔢 尺寸基准": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 8, "tooltip": "仅在按长/短边缩放模式下有效"}),
                "↔️ 目标宽度": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8}),
                "↕️ 目标高度": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8}),
                "📍 裁剪位置": (["居中", "顶部居中", "底部居中", "左侧居中", "右侧居中", "左上", "右上", "左下", "右下"], {"default": "居中"}),
                "🔨 采样算法": (["nearest", "bilinear", "bicubic", "lanczos"], {"default": "lanczos"}),
            },
            "optional": {
                "🖼️ 图像输入": ("IMAGE",),
                "📂 本地文件夹路径": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("🖼️ 处理后图像",)
    FUNCTION = "batch_resize"
    CATEGORY = "🤖Dapao-Toolbox"
    INPUT_IS_LIST = True

    def batch_resize(self, **kwargs):
        # 提取参数 (由于 INPUT_IS_LIST=True, 所有输入都是列表，需要解包)
        mode = kwargs.get("📊 缩放模式", ["✂️ 缩放并裁剪至指定尺寸"])[0]
        size_value = kwargs.get("🔢 尺寸基准", [1024])[0]
        target_w = kwargs.get("↔️ 目标宽度", [512])[0]
        target_h = kwargs.get("↕️ 目标高度", [512])[0]
        crop_pos = kwargs.get("📍 裁剪位置", ["居中"])[0]
        algo_str = kwargs.get("🔨 采样算法", ["lanczos"])[0]
        
        images_input = kwargs.get("🖼️ 图像输入", None)
        folder_path_list = kwargs.get("📂 本地文件夹路径", [""])
        folder_path = folder_path_list[0] if folder_path_list else ""

        # 映射采样算法
        algo_map = {
            "nearest": Image.NEAREST,
            "bilinear": Image.BILINEAR,
            "bicubic": Image.BICUBIC,
            "lanczos": Image.LANCZOS
        }
        resample_algo = algo_map.get(algo_str, Image.LANCZOS)

        pil_images = []

        # 1. 处理图像输入
        if images_input is not None:
            # images_input 是一个列表，里面可能包含多个 Tensor [B, H, W, C]
            for img_batch in images_input:
                if isinstance(img_batch, torch.Tensor):
                    # [B, H, W, C] -> split to single images
                    for i in range(img_batch.shape[0]):
                        pil_img = self.tensor_to_pil(img_batch[i])
                        pil_images.append(pil_img)

        # 2. 处理文件夹输入
        if folder_path and os.path.isdir(folder_path):
            valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
            try:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if os.path.splitext(file)[1].lower() in valid_exts:
                            try:
                                img_path = os.path.join(root, file)
                                pil_img = Image.open(img_path)
                                # 统一转为 RGBA 或 RGB，避免后续处理出错
                                if pil_img.mode not in ["RGB", "RGBA"]:
                                    pil_img = pil_img.convert("RGBA")
                                pil_images.append(pil_img)
                            except Exception as e:
                                print(f"DapaoBatchImageResize: Failed to load {file}: {e}")
            except Exception as e:
                print(f"DapaoBatchImageResize: Error reading folder {folder_path}: {e}")

        if not pil_images:
            # 如果没有图片，返回一个空的 Tensor (1, 1, 1, 3) 避免报错，或者直接报错
            # 这里选择返回空列表，但 ComfyUI 下游可能会报错
            print("DapaoBatchImageResize: No images found.")
            return ([],)

        processed_images = []

        for img in pil_images:
            w, h = img.size
            new_img = None

            if mode == "📏 按长边缩放":
                scale = size_value / max(w, h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                new_img = img.resize((new_w, new_h), resample=resample_algo)

            elif mode == "📐 按短边缩放":
                scale = size_value / min(w, h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                new_img = img.resize((new_w, new_h), resample=resample_algo)

            elif mode == "🔢 强制拉伸至指定尺寸":
                new_img = img.resize((target_w, target_h), resample=resample_algo)

            elif mode == "✂️ 缩放并裁剪至指定尺寸":
                # 核心逻辑：先缩放（覆盖），再裁剪
                # 计算覆盖所需的比例
                scale_w = target_w / w
                scale_h = target_h / h
                scale = max(scale_w, scale_h) # 取最大值以确保覆盖
                
                resize_w = int(w * scale)
                resize_h = int(h * scale)
                
                # 为了精度，向上取整或多加一点点防止黑边？int转换通常向下取整。
                # 如果 resize_w < target_w (由于精度丢失)，会有黑边。
                # 建议使用 math.ceil 或者 +0.5
                if resize_w < target_w: resize_w = target_w
                if resize_h < target_h: resize_h = target_h

                img_resized = img.resize((resize_w, resize_h), resample=resample_algo)
                
                # 裁剪逻辑
                left, top = 0, 0
                if crop_pos == "居中":
                    left = (resize_w - target_w) // 2
                    top = (resize_h - target_h) // 2
                elif crop_pos == "顶部居中":
                    left = (resize_w - target_w) // 2
                    top = 0
                elif crop_pos == "底部居中":
                    left = (resize_w - target_w) // 2
                    top = resize_h - target_h
                elif crop_pos == "左侧居中":
                    left = 0
                    top = (resize_h - target_h) // 2
                elif crop_pos == "右侧居中":
                    left = resize_w - target_w
                    top = (resize_h - target_h) // 2
                elif crop_pos == "左上":
                    left = 0
                    top = 0
                elif crop_pos == "右上":
                    left = resize_w - target_w
                    top = 0
                elif crop_pos == "左下":
                    left = 0
                    top = resize_h - target_h
                elif crop_pos == "右下":
                    left = resize_w - target_w
                    top = resize_h - target_h
                
                right = left + target_w
                bottom = top + target_h
                
                new_img = img_resized.crop((left, top, right, bottom))

            if new_img:
                processed_images.append(self.pil_to_tensor(new_img))

        # 尝试堆叠 Tensor
        # 只有当所有图像尺寸一致时才能 stack
        if not processed_images:
            return ([],)

        first_shape = processed_images[0].shape
        can_stack = True
        for p_img in processed_images:
            if p_img.shape != first_shape:
                can_stack = False
                break
        
        if can_stack:
            # stack [1, H, W, C] -> [B, H, W, C]
            output_tensor = torch.cat(processed_images, dim=0)
            return (output_tensor,)
        else:
            # 返回列表，ComfyUI 应该能处理 list of tensors (如果不 stack)
            # 但是标准的 ComfyUI 节点下游通常期望 Tensor Batch。
            # 如果不能 stack，直接返回 list。
            # 下游节点如果不开启 INPUT_IS_LIST 可能会只处理第一个或者报错。
            # 但作为 ToolBox，尽量兼容。
            return (processed_images,)

    def tensor_to_pil(self, tensor):
        # tensor: [H, W, C]
        return Image.fromarray(np.clip(255. * tensor.cpu().numpy(), 0, 255).astype(np.uint8))

    def pil_to_tensor(self, pil_image):
        # return: [1, H, W, C]
        return torch.from_numpy(np.array(pil_image).astype(np.float32) / 255.0).unsqueeze(0)

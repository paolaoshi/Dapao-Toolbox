import torch
import numpy as np
import os
import io
from PIL import Image, ImageOps

class DapaoBatchImageResize:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "📊 缩放模式": (["📏 按长边缩放", "📐 按短边缩放", "🔢 强制拉伸至指定尺寸", "✂️ 缩放并裁剪至指定尺寸"], {"default": "✂️ 缩放并裁剪至指定尺寸"}),
                "🔢 缩放基准": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 8, "tooltip": "⚠️注意：仅在[按长边/短边缩放]模式下生效！决定缩放后的基准尺寸。"}),
                "↔️ 裁剪宽度": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8, "tooltip": "⚠️注意：仅在[强制拉伸]和[缩放并裁剪]模式下生效！"}),
                "↕️ 裁剪高度": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8, "tooltip": "⚠️注意：仅在[强制拉伸]和[缩放并裁剪]模式下生效！"}),
                "📍 裁剪位置": (["居中", "顶部居中", "底部居中", "左侧居中", "右侧居中", "左上", "右上", "左下", "右下"], {"default": "居中"}),
                "🔨 采样算法": (["nearest", "bilinear", "bicubic", "lanczos"], {"default": "lanczos"}),
                "💾 保存模式": (["❌ 不保存 (仅预览)", "⚠️ 覆盖原文件", "📁 保存到新文件夹"], {"default": "❌ 不保存 (仅预览)"}),
                "📂 输出文件夹名": ("STRING", {"default": "resized_output", "multiline": False, "tooltip": "仅在'保存到新文件夹'模式下有效，将在原图片目录下创建此文件夹"}),
                "💾 限制文件大小 (MB)": ("FLOAT", {"default": 0, "min": 0, "max": 100, "step": 0.1, "tooltip": "0表示不限制。仅对支持压缩的格式(如JPG/WEBP)有效"}),
                "📉 保存质量": ("INT", {"default": 95, "min": 1, "max": 100, "step": 1, "tooltip": "保存图片的质量 (1-100)"}),
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
    OUTPUT_NODE = True

    def batch_resize(self, **kwargs):
        # 提取参数
        mode = kwargs.get("📊 缩放模式", ["✂️ 缩放并裁剪至指定尺寸"])[0]
        size_value = kwargs.get("🔢 缩放基准", [1024])[0]
        target_w = kwargs.get("↔️ 裁剪宽度", [512])[0]
        target_h = kwargs.get("↕️ 裁剪高度", [512])[0]
        crop_pos = kwargs.get("📍 裁剪位置", ["居中"])[0]
        algo_str = kwargs.get("🔨 采样算法", ["lanczos"])[0]
        
        save_mode = kwargs.get("💾 保存模式", ["❌ 不保存 (仅预览)"])[0]
        output_folder_name = kwargs.get("📂 输出文件夹名", ["resized_output"])[0]
        max_file_size_mb = kwargs.get("💾 限制文件大小 (MB)", [0])[0]
        save_quality = kwargs.get("📉 保存质量", [95])[0]

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

        # 维护一个 (pil_img, original_path) 的列表
        # original_path 为 None 表示来自 Tensor 输入，无法覆盖保存
        image_data_list = []

        # 1. 处理图像输入 (Tensor)
        if images_input is not None:
            for img_batch in images_input:
                if isinstance(img_batch, torch.Tensor):
                    for i in range(img_batch.shape[0]):
                        pil_img = self.tensor_to_pil(img_batch[i])
                        image_data_list.append((pil_img, None))

        # 2. 处理文件夹输入
        if folder_path and os.path.isdir(folder_path):
            valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
            try:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if ext in valid_exts:
                            try:
                                img_path = os.path.join(root, file)
                                pil_img = Image.open(img_path)
                                # 统一转为 RGBA 或 RGB
                                if pil_img.mode not in ["RGB", "RGBA"]:
                                    pil_img = pil_img.convert("RGBA")
                                image_data_list.append((pil_img, img_path))
                            except Exception as e:
                                print(f"DapaoBatchImageResize: Failed to load {file}: {e}")
            except Exception as e:
                print(f"DapaoBatchImageResize: Error reading folder {folder_path}: {e}")

        if not image_data_list:
            print("DapaoBatchImageResize: No images found.")
            return ([],)

        processed_images = []

        for pil_img, original_path in image_data_list:
            w, h = pil_img.size
            new_img = None

            # --- 缩放/裁剪逻辑 ---
            if mode == "📏 按长边缩放":
                scale = size_value / max(w, h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                new_img = pil_img.resize((new_w, new_h), resample=resample_algo)

            elif mode == "📐 按短边缩放":
                scale = size_value / min(w, h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                new_img = pil_img.resize((new_w, new_h), resample=resample_algo)

            elif mode == "🔢 强制拉伸至指定尺寸":
                new_img = pil_img.resize((target_w, target_h), resample=resample_algo)

            elif mode == "✂️ 缩放并裁剪至指定尺寸":
                scale_w = target_w / w
                scale_h = target_h / h
                scale = max(scale_w, scale_h)
                
                resize_w = int(w * scale)
                resize_h = int(h * scale)
                
                if resize_w < target_w: resize_w = target_w
                if resize_h < target_h: resize_h = target_h

                img_resized = pil_img.resize((resize_w, resize_h), resample=resample_algo)
                
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
                # 添加到输出列表
                processed_images.append(self.pil_to_tensor(new_img))
                
                # --- 保存逻辑 ---
                if save_mode != "❌ 不保存 (仅预览)" and original_path:
                    try:
                        save_path = ""
                        # 确定保存路径
                        if save_mode == "⚠️ 覆盖原文件":
                            save_path = original_path
                        elif save_mode == "📁 保存到新文件夹":
                            dir_name = os.path.dirname(original_path)
                            file_name = os.path.basename(original_path)
                            new_dir = os.path.join(dir_name, output_folder_name)
                            if not os.path.exists(new_dir):
                                os.makedirs(new_dir)
                            save_path = os.path.join(new_dir, file_name)
                        
                        # 确定保存格式
                        ext = os.path.splitext(save_path)[1].lower()
                        format_map = {
                            '.jpg': 'JPEG', '.jpeg': 'JPEG',
                            '.png': 'PNG', '.webp': 'WEBP',
                            '.bmp': 'BMP', '.tiff': 'TIFF'
                        }
                        # 如果没有扩展名或者不识别，默认用 PNG (如果是另存为，应该有扩展名；如果是覆盖，肯定有)
                        save_format = format_map.get(ext, 'PNG')

                        # 处理 RGBA -> RGB (如果保存为 JPEG)
                        img_to_save = new_img
                        if save_format == 'JPEG' and img_to_save.mode == 'RGBA':
                            img_to_save = img_to_save.convert('RGB')

                        # --- 文件大小限制逻辑 ---
                        current_quality = save_quality
                        
                        # 只有支持质量参数的格式才进行循环压缩
                        if max_file_size_mb > 0 and save_format in ['JPEG', 'WEBP']:
                            target_size_bytes = max_file_size_mb * 1024 * 1024
                            min_quality = 10
                            
                            # 二分法查找合适的 quality
                            # 实际上简单的循环递减可能更稳健，或者多次尝试
                            # 这里采用简单的尝试：如果大了，就降质量
                            
                            # 第一次尝试
                            img_byte_arr = io.BytesIO()
                            img_to_save.save(img_byte_arr, format=save_format, quality=current_quality)
                            size = img_byte_arr.tell()
                            
                            if size > target_size_bytes:
                                # 循环降低质量
                                while size > target_size_bytes and current_quality > min_quality:
                                    current_quality -= 5
                                    img_byte_arr = io.BytesIO()
                                    img_to_save.save(img_byte_arr, format=save_format, quality=current_quality)
                                    size = img_byte_arr.tell()
                                
                            # 保存最终结果
                            with open(save_path, "wb") as f:
                                f.write(img_byte_arr.getbuffer())
                                
                        else:
                            # 不限制大小或不支持压缩的格式，直接保存
                            if save_format in ['JPEG', 'WEBP']:
                                img_to_save.save(save_path, quality=current_quality)
                            else:
                                img_to_save.save(save_path)
                                
                        print(f"DapaoBatchImageResize: Saved {save_path}")

                    except Exception as e:
                        print(f"DapaoBatchImageResize: Error saving {original_path}: {e}")

        # 堆叠 Tensor
        if not processed_images:
            return ([],)

        first_shape = processed_images[0].shape
        can_stack = True
        for p_img in processed_images:
            if p_img.shape != first_shape:
                can_stack = False
                break
        
        if can_stack:
            output_tensor = torch.cat(processed_images, dim=0)
            return (output_tensor,)
        else:
            return (processed_images,)

    def tensor_to_pil(self, tensor):
        return Image.fromarray(np.clip(255. * tensor.cpu().numpy(), 0, 255).astype(np.uint8))

    def pil_to_tensor(self, pil_image):
        return torch.from_numpy(np.array(pil_image).astype(np.float32) / 255.0).unsqueeze(0)

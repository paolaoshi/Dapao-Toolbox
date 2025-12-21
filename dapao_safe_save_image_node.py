import os
import json
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import folder_paths
import torch
import random
import string

class DapaoSafeSaveImage:
    """
    😶‍🌫️安全保存图像@炮老师的小课堂
    
    功能：
    - 保存图像时自动移除所有元数据（工作流信息、提示词等）
    - 保护用户隐私，生成的图片不包含 ComfyUI 的生成信息
    - 支持多种格式（PNG, JPG, WEBP）
    - 支持自定义压缩质量
    """
    
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "🖼️ 图像": ("IMAGE", {"tooltip": "需要保存的图像批次"}),
                "📄 文件名前缀": ("STRING", {"default": "dapao", "tooltip": "文件名前缀"}),
                "💾 格式": (["PNG", "JPG", "WEBP"], {"default": "PNG", "tooltip": "保存的文件格式"}),
                "📉 质量": ("INT", {"default": 100, "min": 1, "max": 100, "step": 1, "tooltip": "图片质量 (1-100)，对 JPG/WEBP 有效"}),
                "😶‍🌫️ 移除元数据": ("BOOLEAN", {"default": True, "label_on": "开启隐私保护 (移除元数据)", "label_off": "关闭 (保留元数据)", "tooltip": "是否移除图像中的工作流信息和生成参数"}),
            },
            "optional": {
                "📂 自定义路径": ("STRING", {"default": "", "tooltip": "自定义保存路径，留空则使用默认路径"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "🤖Dapao-Toolbox"

    def save_images(self, **kwargs):
        # 参数映射
        images = kwargs.get("🖼️ 图像")
        filename_prefix = kwargs.get("📄 文件名前缀", "dapao")
        format = kwargs.get("💾 格式", "PNG")
        quality = kwargs.get("📉 质量", 100)
        remove_metadata = kwargs.get("😶‍🌫️ 移除元数据", True)
        custom_path = kwargs.get("📂 自定义路径", "").strip()
        prompt = kwargs.get("prompt", None)
        extra_pnginfo = kwargs.get("extra_pnginfo", None)

        filename_prefix += self.prefix_append
        
        # 确定基础保存路径
        base_output_dir = self.output_dir
        if custom_path:
            try:
                os.makedirs(custom_path, exist_ok=True)
                base_output_dir = custom_path
            except Exception as e:
                print(f"Error creating custom path '{custom_path}', falling back to default. Error: {e}")

        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, base_output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
        
        # 确定文件扩展名
        extension = format.lower()
        if extension == "jpg":
            extension = "jpeg"
            
        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # 处理元数据
            metadata = None
            if not remove_metadata:
                if format == "PNG":
                    metadata = PngInfo()
                    if prompt is not None:
                        metadata.add_text("prompt", json.dumps(prompt))
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                # JPG/WEBP 的 metadata 处理比较复杂，ComfyUI 默认主要支持 PNG metadata
                # 这里为了简化和安全，非 PNG 格式且 remove_metadata=False 时，我们也不强制写入 Exif，
                # 因为主要目的是"安全保存"，开启隐私保护时必须清空。
            
            # 生成文件名
            file = f"{filename}_{counter:05}_.{extension}"
            
            # 保存参数准备
            save_kwargs = {}
            if format == "PNG":
                if remove_metadata:
                    save_kwargs["pnginfo"] = None
                else:
                    save_kwargs["pnginfo"] = metadata
                save_kwargs["compress_level"] = 4 # 默认压缩等级
            elif format in ["JPG", "JPEG"]:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            elif format == "WEBP":
                save_kwargs["quality"] = quality
                save_kwargs["method"] = 6
            
            # 如果是 JPG，需要转换模式，不能有 Alpha 通道
            if format in ["JPG", "JPEG"] and img.mode == "RGBA":
                img = img.convert("RGB")
                
            # 执行保存
            try:
                img.save(os.path.join(full_output_folder, file), **save_kwargs)
            except Exception as e:
                print(f"Error saving image: {e}")
                
            # 标准返回结果
            results_item = {
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            }

            # 如果使用了自定义路径，为了能在前端预览，我们需要额外保存一份副本到 ComfyUI 的 temp 目录
            if custom_path:
                try:
                    # 获取临时目录
                    temp_dir = folder_paths.get_temp_directory()
                    
                    # 生成随机文件名，避免缓存冲突
                    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                    temp_filename = f"dapao_preview_{random_suffix}.{extension}"
                    
                    # 保存临时文件（始终移除 metadata 以减小体积和保护隐私，且仅作为预览）
                    # 注意：预览图强制转为 WebP 或 JPG 以节省带宽，或者保持原格式
                    # 这里为了简单，直接保存一份原图
                    img.save(os.path.join(temp_dir, temp_filename), **save_kwargs)
                    
                    # 更新返回给前端的预览信息指向临时文件
                    results_item = {
                        "filename": temp_filename,
                        "subfolder": "",
                        "type": "temp"
                    }
                except Exception as e:
                    print(f"Error saving preview image to temp: {e}")
            
            results.append(results_item)
            counter += 1

        return { "ui": { "images": results } }

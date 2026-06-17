import os
import torch
import numpy as np
from PIL import Image, ImageOps

class DapaoLoadFolderImages:
    """
    🦁文件夹加载图像@炮老师的小课堂
    
    功能：
    - 从指定文件夹加载图片序列
    - 支持排序、数量限制、起始索引
    - 智能批次尺寸统一（支持按首图或指定尺寸）
    - 支持限制最长边（优化显存）
    - 灵活的适配模式（默认/裁剪/填充/拉伸）
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "📂 文件夹路径": ("STRING", {"default": "", "multiline": False, "tooltip": "图片所在的文件夹路径"}),
                "🔢 加载数量": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "限制加载图片的数量，0表示加载所有"}),
                "🏁 起始索引": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "跳过前N张图片"}),
                "🔄 排序方式": (["文件名升序 (A-Z)", "文件名降序 (Z-A)", "日期 (最新在前)", "日期 (最旧在前)", "随机"], {"default": "文件名升序 (A-Z)"}),
                "📐 统一尺寸规则": (["统一为首图尺寸", "指定固定尺寸"], {"default": "统一为首图尺寸"}),
                "↔️ 指定宽度": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8, "tooltip": "仅在选择'指定固定尺寸'时生效"}),
                "↕️ 指定高度": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 8, "tooltip": "仅在选择'指定固定尺寸'时生效"}),
                "📏 限制最长边": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 64, "tooltip": "预处理：将图片最长边限制在指定像素内（0不限制）。对'统一为首图尺寸'模式有效，可减小显存占用"}),
                "🛠️ 适配模式": (["默认", "保持比例-填充黑边", "保持比例-居中裁剪", "拉伸"], {"default": "默认", "tooltip": "默认模式不改变原图；其他模式会统一到目标批次尺寸"}),
                "🎨 填充颜色": ("STRING", {"default": "#000000", "tooltip": "填充黑边时的背景颜色（Hex格式）"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "INT", "STRING")
    RETURN_NAMES = ("🖼️ 图像批次", "🖼️ 图像列表", "🔢 数量", "📂 文件名列表")
    OUTPUT_IS_LIST = (False, True, False, False)
    FUNCTION = "load_images"
    CATEGORY = "🤖Dapao-Toolbox"

    def load_images(self, **kwargs):
        folder_path = kwargs["📂 文件夹路径"]
        cap = kwargs["🔢 加载数量"]
        start_index = kwargs["🏁 起始索引"]
        sort_method = kwargs["🔄 排序方式"]
        size_rule = kwargs["📐 统一尺寸规则"]
        fixed_w = kwargs["↔️ 指定宽度"]
        fixed_h = kwargs["↕️ 指定高度"]
        limit_max_side = kwargs["📏 限制最长边"]
        fit_mode = kwargs["🛠️ 适配模式"]
        pad_color_hex = kwargs["🎨 填充颜色"]

        # 1. 验证路径
        if not os.path.isdir(folder_path):
            # 尝试去掉可能存在的引号
            folder_path = folder_path.strip('"').strip("'")
            if not os.path.isdir(folder_path):
                raise ValueError(f"❌ 错误：文件夹路径不存在 -> {folder_path}")

        # 2. 获取文件列表
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.gif'}
        files = []
        for f in os.listdir(folder_path):
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_extensions:
                files.append(os.path.join(folder_path, f))
        
        if not files:
            raise ValueError("❌ 错误：文件夹内未找到支持的图片文件")

        # 3. 排序
        if sort_method == "文件名升序 (A-Z)":
            files.sort()
        elif sort_method == "文件名降序 (Z-A)":
            files.sort(reverse=True)
        elif sort_method == "日期 (最新在前)":
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        elif sort_method == "日期 (最旧在前)":
            files.sort(key=lambda x: os.path.getmtime(x))
        elif sort_method == "随机":
            import random
            random.shuffle(files)

        # 4. 截取范围
        if start_index > 0:
            files = files[start_index:]
        if cap > 0:
            files = files[:cap]
            
        if not files:
            print("⚠️ 警告：经过筛选后没有图片可加载")
            # 返回一个空的 1x1 黑色图像以防报错
            empty = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
            return (empty, [empty], 0, [])

        # 5. 确定目标尺寸。默认模式保留原图尺寸，不使用目标尺寸处理。
        target_w, target_h = 0, 0
        
        if fit_mode == "默认":
            target_w, target_h = None, None
        elif size_rule == "指定固定尺寸":
            target_w, target_h = fixed_w, fixed_h
        else:
            # 读取第一张图作为基准
            try:
                first_img = Image.open(files[0])
                w, h = first_img.size
                
                # 如果有最长边限制，先应用到基准尺寸
                if limit_max_side > 0:
                    scale = min(1.0, limit_max_side / max(w, h))
                    if scale < 1.0:
                        w = int(w * scale)
                        h = int(h * scale)
                
                target_w, target_h = w, h
            except Exception as e:
                raise ValueError(f"❌ 读取首图失败: {e}")

        # 解析填充颜色
        try:
            c = pad_color_hex.lstrip('#')
            rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
            pad_color = rgb
        except:
            pad_color = (0, 0, 0)

        # 6. 逐个处理加载
        image_list = []
        filename_list = []
        
        for file_path in files:
            try:
                img = Image.open(file_path)
                # 转换颜色空间
                img = ImageOps.exif_transpose(img) # 处理旋转信息
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 预处理：限制单图最大边（如果是统一首图模式，这一步有助于减少中间内存；如果是固定尺寸，直接缩放到固定尺寸更优，但为了逻辑统一...）
                # 其实如果 fit_mode 是拉伸或填充，我们最终都要 resize 到 target_w/h。
                # 这里的 limit_max_side 主要是为了防止加载巨型图片导致处理过程崩掉
                if limit_max_side > 0 and size_rule == "统一为首图尺寸":
                     # 只有在非固定尺寸模式下，单独限制才有意义？
                     # 不，如果目标就是固定尺寸，那直接缩放到 target 即可。
                     # 如果是统一首图，首图已经限制了 target。
                     # 那么后续图片是否需要先 limit 再 fit? 
                     # 直接 Fit 到 Target 即可。
                     pass

                processed_img = self.process_image(img, target_w, target_h, fit_mode, pad_color)
                
                # 转 Tensor
                img_np = np.array(processed_img).astype(np.float32) / 255.0
                image_list.append(torch.from_numpy(img_np))
                filename_list.append(os.path.basename(file_path))
                
            except Exception as e:
                print(f"⚠️ 跳过损坏或无法读取的图片: {file_path} -> {e}")
                continue

        if not image_list:
             raise ValueError("❌ 错误：所有图片处理失败")

        image_output_list = [img.unsqueeze(0) for img in image_list]
        try:
            output_images = torch.stack(image_list, dim=0) # [B, H, W, C]
        except RuntimeError:
            if fit_mode != "默认":
                raise
            output_images = self.pad_images_to_max_size(image_list, pad_color)
            print("⚠️ 默认模式检测到图片尺寸不一致：图像列表输出保留原图尺寸，图像批次输出已补边到最大尺寸以便组成批次。")
        
        return (output_images, image_output_list, len(image_list), filename_list)

    def pad_images_to_max_size(self, image_list, pad_color):
        max_h = max(img.shape[0] for img in image_list)
        max_w = max(img.shape[1] for img in image_list)
        fill = torch.tensor(pad_color, dtype=image_list[0].dtype) / 255.0

        padded = []
        for img in image_list:
            h, w, c = img.shape
            canvas = fill.reshape(1, 1, 3).repeat(max_h, max_w, 1)
            top = (max_h - h) // 2
            left = (max_w - w) // 2
            canvas[top:top + h, left:left + w, :c] = img
            padded.append(canvas)
        return torch.stack(padded, dim=0)

    def process_image(self, img, target_w, target_h, mode, pad_color):
        if mode == "默认":
            return img

        if img.size == (target_w, target_h):
            return img
            
        if mode == "拉伸":
            return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
        elif mode == "保持比例-居中裁剪":
            # Aspect Fill
            img_w, img_h = img.size
            scale = max(target_w / img_w, target_h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            return resized.crop((left, top, left + target_w, top + target_h))
            
        else: # 保持比例-填充黑边 (Aspect Fit)
            img_w, img_h = img.size
            scale = min(target_w / img_w, target_h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            new_img = Image.new("RGB", (target_w, target_h), pad_color)
            left = (target_w - new_w) // 2
            top = (target_h - new_h) // 2
            new_img.paste(resized, (left, top))
            return new_img

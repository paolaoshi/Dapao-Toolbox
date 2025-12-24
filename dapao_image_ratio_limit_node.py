import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class DapaoImageRatioLimitNode:
    """
    图像比尺寸限定节点
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # 生成 0.1 到 2.5 的百万像素选项，步长 0.1
        megapixel_options = [f"{i/10:.1f}" for i in range(1, 26)]
        
        return {
            "required": {
                "🔢 百万像素": (megapixel_options, {"default": "1.0", "tooltip": "目标图像的总像素数（百万级）"}),
                "📐 宽高比": ([
                    "1:1 (正方形)",
                    "2:3 (经典竖屏)", "3:4 (黄金比例竖)", "3:5 (优雅竖屏)", "4:5 (艺术画框竖)", "5:7 (标准竖屏)", "5:8 (高耸竖屏)",
                    "7:9 (现代竖屏)", "9:16 (手机竖屏)", "9:19 (高瘦竖屏)", "9:21 (超高竖屏)", "9:32 (摩天大楼)",
                    "3:2 (经典横屏)", "4:3 (黄金比例横)", "5:3 (宽视野)", "5:4 (平衡画框横)", "7:5 (优雅横屏)", "8:5 (电影视角)",
                    "9:7 (艺术横屏)", "16:9 (电脑屏幕)", "19:9 (电影超宽)", "21:9 (史诗超宽)", "32:9 (极限超宽)"
                ], {"default": "1:1 (正方形)", "tooltip": "预设的宽高比"}),
                "🔢 整除倍数": (["8", "16", "32", "64"], {"default": "64", "tooltip": "宽高数值必须能被此数整除"}),
                "🔘 启用自定义比例": ("BOOLEAN", {"default": False, "label_on": "启用", "label_off": "禁用", "tooltip": "是否使用下方自定义宽高比"}),
            },
            "optional": {
                "✏️ 自定义宽高比": ("STRING", {"default": "1:1", "tooltip": "格式如 16:9"}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING", "IMAGE")
    RETURN_NAMES = ("↔️ 宽度", "↕️ 高度", "📝 分辨率信息", "🖼️ 预览图")
    FUNCTION = "calculate_dimensions"
    CATEGORY = "🤖Dapao-Toolbox"
    OUTPUT_NODE = True

    def create_preview_image(self, width, height, resolution, ratio_display):
        # 1024x1024 预览画布
        preview_size = (1024, 1024)
        image = Image.new('RGB', preview_size, (0, 0, 0))  # 黑色背景
        draw = ImageDraw.Draw(image)

        # 绘制深灰色网格
        grid_color = '#333333'
        grid_spacing = 50
        for x in range(0, preview_size[0], grid_spacing):
            draw.line([(x, 0), (x, preview_size[1])], fill=grid_color)
        for y in range(0, preview_size[1], grid_spacing):
            draw.line([(0, y), (preview_size[0], y)], fill=grid_color)

        # 计算预览框尺寸（最大800像素）
        preview_width = 800
        preview_height = int(preview_width * (height / width))
        
        # 如果高度过高，则以高度为基准
        if preview_height > 800:
            preview_height = 800
            preview_width = int(preview_height * (width / height))

        # 计算居中位置
        x_offset = (preview_size[0] - preview_width) // 2
        y_offset = (preview_size[1] - preview_height) // 2

        # 绘制红框
        draw.rectangle(
            [(x_offset, y_offset), (x_offset + preview_width, y_offset + preview_height)],
            outline='red',
            width=4
        )

        # 绘制文本
        try:
            # 计算文本位置
            text_y = y_offset + preview_height // 2
            
            # 分辨率文本 (红色)
            font_size_large = 48
            font_size_medium = 36
            font_size_small = 32
            
            # 尝试加载默认字体，如果失败则使用默认字体对象
            try:
                font_large = ImageFont.truetype("arial.ttf", font_size_large)
                font_medium = ImageFont.truetype("arial.ttf", font_size_medium)
                font_small = ImageFont.truetype("arial.ttf", font_size_small)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()

            draw.text((preview_size[0]//2, text_y), 
                     f"{width}x{height}", 
                     fill='red', 
                     anchor="mm",
                     font=font_large)
            
            # 比例文本 (红色)
            draw.text((preview_size[0]//2, text_y + 60),
                     f"({ratio_display})",
                     fill='red',
                     anchor="mm",
                     font=font_medium)
            
            # 底部信息文本 (白色)
            draw.text((preview_size[0]//2, y_offset + preview_height + 60),
                     f"Resolution: {resolution}",
                     fill='white',
                     anchor="mm",
                     font=font_small)
            
        except Exception as e:
            print(f"DapaoImageRatioLimitNode: Error drawing text - {e}")

        # 转换为 Tensor
        return self.pil2tensor(image)

    def calculate_dimensions(self, **kwargs):
        # 获取参数
        megapixel = float(kwargs.get("🔢 百万像素", "1.0"))
        aspect_ratio_str = kwargs.get("📐 宽高比", "1:1 (正方形)")
        divisible_by = int(kwargs.get("🔢 整除倍数", "64"))
        use_custom = kwargs.get("🔘 启用自定义比例", False)
        custom_ratio_str = kwargs.get("✏️ 自定义宽高比", "1:1")

        if use_custom and custom_ratio_str:
            numeric_ratio = custom_ratio_str
            ratio_display = custom_ratio_str
        else:
            numeric_ratio = aspect_ratio_str.split(' ')[0]
            ratio_display = numeric_ratio
        
        try:
            width_ratio, height_ratio = map(int, numeric_ratio.split(':'))
        except ValueError:
            # 容错处理：如果格式错误，默认 1:1
            width_ratio, height_ratio = 1, 1
            print(f"DapaoImageRatioLimitNode: Invalid ratio format '{numeric_ratio}', using 1:1")
        
        total_pixels = megapixel * 1_000_000
        dimension = (total_pixels / (width_ratio * height_ratio)) ** 0.5
        width = int(dimension * width_ratio)
        height = int(dimension * height_ratio)

        # 应用整除倍数
        width = round(width / divisible_by) * divisible_by
        height = round(height / divisible_by) * divisible_by
        
        # 防止 0 尺寸
        width = max(divisible_by, width)
        height = max(divisible_by, height)

        resolution = f"{width} x {height}"
        
        # 生成预览图
        preview = self.create_preview_image(width, height, resolution, ratio_display)
        
        return (width, height, resolution, preview)

    def pil2tensor(self, image):
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

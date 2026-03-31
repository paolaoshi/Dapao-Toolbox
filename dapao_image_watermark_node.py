import os
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageChops


class DapaoImageWatermarkNode:
    """
    🐥图像水印节点 - 支持文字水印与图像水印

    功能说明：
    - 支持为图像添加文字水印
    - 支持为图像添加图像水印
    - 支持单个水印与平铺水印
    - 支持透明度、角度、位置、偏移等常用参数
    - 支持输出透明通道

    Time: 2026/03/31
    Author: Dapao
    """

    def __init__(self):
        self.font_directories = self._get_font_directories()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "🖼️ 输入图像": ("IMAGE", {"tooltip": "需要添加水印的原始图像"}),
                "📝 水印文本": ("STRING", {"default": "炮老师的小课堂", "multiline": False, "tooltip": "文字水印内容"}),
                "🔤 水印字体": (cls._get_font_options(), {"tooltip": "用于文字水印的字体"}),
                "🔠 水印大小百分比": ("INT", {"default": 5, "min": 1, "max": 100, "step": 1, "tooltip": "文字大小按底图高度百分比计算；图像水印可按原尺寸或底图尺寸比例缩放"}),
                "🫥 水印不透明度": ("INT", {"default": 50, "min": 0, "max": 100, "step": 1, "tooltip": "水印整体不透明度"}),
                "🖼️ 水印混合模式": (["正常", "正片叠底", "滤色", "叠加", "柔光"], {"default": "正常", "tooltip": "控制水印与底图的混合方式"}),
                "↔️ 水平位置": (["居中", "靠左", "靠右"], {"default": "居中", "tooltip": "水印在水平方向的位置"}),
                "↕️ 垂直位置": (["居中", "靠上", "靠下"], {"default": "居中", "tooltip": "水印在垂直方向的位置"}),
                "➡️ X偏移百分比": ("INT", {"default": 0, "min": 0, "max": 50, "step": 1, "tooltip": "基于底图宽度计算的横向偏移百分比"}),
                "⬇️ Y偏移百分比": ("INT", {"default": 0, "min": 0, "max": 50, "step": 1, "tooltip": "基于底图高度计算的纵向偏移百分比"}),
                "🎨 文字颜色": ("COLORCODE", {"default": "#FFFFFF"}),
                "🧱 水印平铺": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭", "tooltip": "开启后以平铺方式重复铺满整张图"}),
                "🔄 水印角度": ("INT", {"default": 0, "min": -90, "max": 90, "step": 1, "tooltip": "水印旋转角度"}),
                "📏 水印间距": ("INT", {"default": 10, "min": 0, "max": 50, "step": 1, "tooltip": "平铺模式下的水印间距百分比"}),
                "📐 按底图比例缩放": ("BOOLEAN", {"default": False, "label_on": "开启", "label_off": "关闭", "tooltip": "仅图像水印生效，开启后按底图最长边百分比缩放"}),
                "🪟 输出透明通道": ("BOOLEAN", {"default": False, "label_on": "保留", "label_off": "关闭", "tooltip": "关闭时会输出普通 RGB 图像"}),
            },
            "optional": {
                "🖼️ 水印图像": ("IMAGE", {"tooltip": "可选，接入后优先使用图像水印而非文字水印"}),
                "😶‍🌫️ 水印遮罩": ("MASK", {"tooltip": "透明 PNG 请把加载图像节点的遮罩口接到这里，用来还原水印透明通道"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("🖼️ 水印图像",)
    FUNCTION = "add_watermark"
    CATEGORY = "🤖Dapao-Toolbox"

    def add_watermark(self, **kwargs):
        """
        为输入图像添加文字或图像水印。

        :param kwargs: 节点输入参数
        :return: 添加水印后的图像

        Time: 2026/03/31
        Author: Dapao
        """
        image_tensor = kwargs["🖼️ 输入图像"]
        watermark_text = kwargs["📝 水印文本"]
        font_name = kwargs["🔤 水印字体"]
        watermark_scale = kwargs["🔠 水印大小百分比"]
        opacity = kwargs["🫥 水印不透明度"]
        horizontal_position = kwargs["↔️ 水平位置"]
        vertical_position = kwargs["↕️ 垂直位置"]
        blend_mode = kwargs["🖼️ 水印混合模式"]
        offset_x_percent = kwargs["➡️ X偏移百分比"]
        offset_y_percent = kwargs["⬇️ Y偏移百分比"]
        text_color = kwargs["🎨 文字颜色"]
        tile_enabled = kwargs["🧱 水印平铺"]
        rotation = kwargs["🔄 水印角度"]
        spacing = kwargs["📏 水印间距"]
        scale_by_base_image = kwargs["📐 按底图比例缩放"]
        keep_alpha = kwargs["🪟 输出透明通道"]
        watermark_image = kwargs.get("🖼️ 水印图像")
        watermark_mask = kwargs.get("😶‍🌫️ 水印遮罩")

        output_images = []
        batch_size = image_tensor.shape[0]

        for batch_index in range(batch_size):
            base_image = self._tensor_to_pil(image_tensor[batch_index]).convert("RGBA")

            if watermark_image is not None:
                current_watermark_image = self._tensor_to_pil(watermark_image[0]).convert("RGBA")
                current_watermark_mask = self._extract_mask_image(watermark_mask)
                if current_watermark_mask is not None:
                    if current_watermark_mask.size != current_watermark_image.size:
                        current_watermark_mask = current_watermark_mask.resize(current_watermark_image.size, Image.Resampling.LANCZOS)
                    current_watermark_image.putalpha(current_watermark_mask)
                result_image = self._apply_image_watermark(
                    base_image=base_image,
                    watermark_image=current_watermark_image,
                    watermark_scale=watermark_scale,
                    opacity=opacity,
                    blend_mode=blend_mode,
                    horizontal_position=horizontal_position,
                    vertical_position=vertical_position,
                    offset_x_percent=offset_x_percent,
                    offset_y_percent=offset_y_percent,
                    rotation=rotation,
                    scale_by_base_image=scale_by_base_image,
                )
            else:
                result_image = self._apply_text_watermark(
                    base_image=base_image,
                    watermark_text=watermark_text,
                    font_name=font_name,
                    watermark_scale=watermark_scale,
                    opacity=opacity,
                    blend_mode=blend_mode,
                    horizontal_position=horizontal_position,
                    vertical_position=vertical_position,
                    offset_x_percent=offset_x_percent,
                    offset_y_percent=offset_y_percent,
                    text_color=text_color,
                    tile_enabled=tile_enabled,
                    rotation=rotation,
                    spacing=spacing,
                )

            if not keep_alpha:
                result_image = result_image.convert("RGB")

            output_images.append(self._pil_to_tensor(result_image))

        return (torch.cat(output_images, dim=0),)

    def _apply_image_watermark(self, base_image, watermark_image, watermark_scale, opacity,
                               blend_mode, horizontal_position, vertical_position,
                               offset_x_percent, offset_y_percent, rotation, scale_by_base_image):
        """应用图像水印。"""
        watermark_width, watermark_height = watermark_image.size
        scale_ratio = max(watermark_scale, 1) / 100.0

        if scale_by_base_image:
            base_long_edge = max(base_image.width, base_image.height)
            watermark_long_edge = max(watermark_width, watermark_height)
            target_long_edge = max(1, int(base_long_edge * scale_ratio))
            resize_ratio = target_long_edge / max(watermark_long_edge, 1)
            target_size = (
                max(1, int(watermark_width * resize_ratio)),
                max(1, int(watermark_height * resize_ratio)),
            )
        else:
            target_size = (
                max(1, int(watermark_width * scale_ratio)),
                max(1, int(watermark_height * scale_ratio)),
            )

        watermark_layer = watermark_image.resize(target_size, Image.Resampling.LANCZOS)

        alpha = watermark_layer.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity / 100.0)
        watermark_layer.putalpha(alpha)

        if rotation != 0:
            watermark_layer = watermark_layer.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)

        x, y = self._calculate_position(
            canvas_width=base_image.width,
            canvas_height=base_image.height,
            overlay_width=watermark_layer.width,
            overlay_height=watermark_layer.height,
            horizontal_position=horizontal_position,
            vertical_position=vertical_position,
            offset_x_percent=offset_x_percent,
            offset_y_percent=offset_y_percent,
        )

        overlay_canvas = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        overlay_canvas.paste(watermark_layer, (x, y), watermark_layer)
        return self._blend_watermark(base_image, overlay_canvas, blend_mode)

    def _apply_text_watermark(self, base_image, watermark_text, font_name, watermark_scale, opacity,
                              blend_mode, horizontal_position, vertical_position,
                              offset_x_percent, offset_y_percent, text_color,
                              tile_enabled, rotation, spacing):
        """应用文字水印。"""
        font_size = max(1, int(base_image.height * (watermark_scale / 100.0)))
        font = self._load_font(font_name, font_size)
        text_width, text_height, baseline_offset = self._measure_text(watermark_text, font)

        margin = max(2, int(font_size * 0.15))
        text_layer = Image.new("RGBA", (text_width + margin * 2, text_height + margin * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        draw.text(
            (margin, margin - baseline_offset),
            watermark_text,
            font=font,
            fill=self._hex_to_rgba(text_color, opacity),
        )

        if rotation != 0:
            text_layer = text_layer.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)

        overlay_canvas = Image.new("RGBA", base_image.size, (0, 0, 0, 0))

        if tile_enabled:
            spacing_pixels = int(base_image.height * (spacing / 100.0))
            step_x = max(1, text_layer.width + spacing_pixels)
            step_y = max(1, text_layer.height + spacing_pixels)
            for x in range(-text_layer.width, base_image.width + text_layer.width, step_x):
                for y in range(-text_layer.height, base_image.height + text_layer.height, step_y):
                    overlay_canvas.paste(text_layer, (x, y), text_layer)
        else:
            x, y = self._calculate_position(
                canvas_width=base_image.width,
                canvas_height=base_image.height,
                overlay_width=text_layer.width,
                overlay_height=text_layer.height,
                horizontal_position=horizontal_position,
                vertical_position=vertical_position,
                offset_x_percent=offset_x_percent,
                offset_y_percent=offset_y_percent,
            )
            overlay_canvas.paste(text_layer, (x, y), text_layer)

        return self._blend_watermark(base_image, overlay_canvas, blend_mode)

    def _blend_watermark(self, base_image, overlay_canvas, blend_mode):
        """按指定混合模式合成水印。"""
        if blend_mode == "正常":
            return Image.alpha_composite(base_image, overlay_canvas)

        base_rgb = base_image.convert("RGB")
        overlay_rgb = overlay_canvas.convert("RGB")

        if blend_mode == "正片叠底":
            blended_rgb = ImageChops.multiply(base_rgb, overlay_rgb)
        elif blend_mode == "滤色":
            blended_rgb = ImageChops.screen(base_rgb, overlay_rgb)
        elif blend_mode == "叠加":
            blended_rgb = ImageChops.overlay(base_rgb, overlay_rgb)
        elif blend_mode == "柔光":
            blended_rgb = ImageChops.soft_light(base_rgb, overlay_rgb)
        else:
            blended_rgb = base_rgb

        blended_rgba = blended_rgb.convert("RGBA")
        blended_rgba.putalpha(base_image.getchannel("A"))
        return Image.composite(blended_rgba, base_image, overlay_canvas.getchannel("A"))

    def _calculate_position(self, canvas_width, canvas_height, overlay_width, overlay_height,
                            horizontal_position, vertical_position, offset_x_percent, offset_y_percent):
        """计算水印位置。"""
        offset_x = int(canvas_width * (offset_x_percent / 100.0))
        offset_y = int(canvas_height * (offset_y_percent / 100.0))

        if horizontal_position == "靠左":
            x = offset_x
        elif horizontal_position == "靠右":
            x = canvas_width - overlay_width - offset_x
        else:
            x = (canvas_width - overlay_width) // 2 + offset_x

        if vertical_position == "靠上":
            y = offset_y
        elif vertical_position == "靠下":
            y = canvas_height - overlay_height - offset_y
        else:
            y = (canvas_height - overlay_height) // 2 + offset_y

        return x, y

    def _measure_text(self, text, font):
        """获取文字尺寸和基线偏移。"""
        temp_image = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp_image)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top, top

    def _load_font(self, font_name, font_size):
        """加载字体，失败则回退默认字体。"""
        font_path = self._resolve_font_path(font_name)
        if font_path:
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception:
                pass
        return ImageFont.load_default()

    @classmethod
    def _get_font_options(cls):
        """获取可选字体列表。"""
        font_names = []
        for font_dir in cls._get_font_directories():
            if not os.path.isdir(font_dir):
                continue
            try:
                for file_name in os.listdir(font_dir):
                    if file_name.lower().endswith((".ttf", ".otf", ".ttc")):
                        font_names.append(file_name)
            except Exception:
                continue

        unique_fonts = sorted(set(font_names))
        if not unique_fonts:
            return ["默认字体"]
        if "默认字体" not in unique_fonts:
            unique_fonts.insert(0, "默认字体")
        return unique_fonts

    @staticmethod
    def _get_font_directories():
        """获取字体搜索目录。"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_font_dir = os.path.join(current_dir, "fonts")
        project_font_dir = os.path.join(os.path.dirname(current_dir), "fonts")
        windows_font_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
        return [local_font_dir, project_font_dir, windows_font_dir]

    def _resolve_font_path(self, font_name):
        """解析字体路径。"""
        if not font_name or font_name == "默认字体":
            return None

        for font_dir in self.font_directories:
            candidate_path = os.path.join(font_dir, font_name)
            if os.path.isfile(candidate_path):
                return candidate_path
        return None

    def _hex_to_rgba(self, hex_color, opacity):
        """将十六进制颜色转为 RGBA。"""
        color_text = str(hex_color).strip().lstrip("#")
        if len(color_text) == 3:
            color_text = "".join(char * 2 for char in color_text)
        if len(color_text) != 6:
            color_text = "FFFFFF"

        red = int(color_text[0:2], 16)
        green = int(color_text[2:4], 16)
        blue = int(color_text[4:6], 16)
        alpha = int(255 * (opacity / 100.0))
        return red, green, blue, alpha

    def _extract_mask_image(self, watermark_mask):
        """将 ComfyUI 的 MASK 输入还原为可用于水印透明通道的灰度图。"""
        if watermark_mask is None:
            return None

        if isinstance(watermark_mask, (list, tuple)):
            watermark_mask = watermark_mask[0] if watermark_mask else None
        if watermark_mask is None:
            return None

        if isinstance(watermark_mask, torch.Tensor):
            mask_tensor = watermark_mask.detach().cpu()
            if mask_tensor.ndim == 3:
                mask_tensor = mask_tensor[0]
            elif mask_tensor.ndim == 4:
                mask_tensor = mask_tensor[0, 0]
            mask_array = 1.0 - mask_tensor.numpy().astype(np.float32)
            mask_array = np.clip(mask_array * 255.0, 0, 255).astype(np.uint8)
            return Image.fromarray(mask_array, mode="L")

        return None

    def _tensor_to_pil(self, image_tensor):
        """将张量转换为 PIL 图像。"""
        image_array = image_tensor.cpu().numpy()
        image_array = np.clip(image_array * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(image_array)

    def _pil_to_tensor(self, image):
        """将 PIL 图像转换为张量。"""
        image_array = np.array(image).astype(np.float32) / 255.0
        if image_array.ndim == 2:
            image_array = np.expand_dims(image_array, axis=-1)
        return torch.from_numpy(image_array).unsqueeze(0)


NODE_CLASS_MAPPINGS = {
    "DapaoImageWatermarkNode": DapaoImageWatermarkNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageWatermarkNode": "🐥图像水印@炮老师的小课堂",
}

import torch
import numpy as np
from PIL import Image, ImageDraw
import json
import os
import hashlib
import folder_paths

class DapaoImageColorBoxNode:
    """
    图像分色框选节点 - 在节点内嵌入画板，支持上传图像后直接绘制
    矩形框、椭圆框、纯色色块，支持多颜色、不透明度、线宽等功能。

    Time: 2026/02/27
    Author: Dapao
    """

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = sorted([
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
            and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))
        ])
        return {
            "required": {
                "image": (files, {}),
                "output_mode": (["合并标注", "仅标注层", "原图"],),
            },
            "optional": {
                "annotations_json": ("STRING", {"default": "[]"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "draw_annotations"
    CATEGORY = "🤖Dapao-Toolbox"

    @classmethod
    def IS_CHANGED(cls, image, annotations_json="[]", output_mode="合并标注"):
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                m.update(f.read())
        m.update(output_mode.encode("utf-8"))
        m.update(annotations_json.encode("utf-8"))
        return m.hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, image, **kwargs):
        if not folder_paths.exists_annotated_filepath(image):
            return f"图像文件不存在: {image}"
        return True

    def draw_annotations(self, image: str, annotations_json: str = "[]",
                         output_mode: str = "合并标注"):
        """
        加载图像并在其上绘制标注框和色块。

        :param image: 图像文件名
        :param annotations_json: 标注数据 JSON 字符串
        :param output_mode: 输出模式
        :return: 标注后的图像张量

        Time: 2026/02/27
        Author: Dapao
        """

        # 加载图像
        image_path = folder_paths.get_annotated_filepath(image)
        pil_img = Image.open(image_path).convert("RGBA")
        img_w, img_h = pil_img.size

        try:
            annotations = json.loads(annotations_json)
        except Exception:
            annotations = []

        if output_mode == "原图":
            out_img = pil_img.convert("RGB")
        else:
            layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
            draw  = ImageDraw.Draw(layer)

            for ann in annotations:
                shape      = ann.get("shape", "rect")
                x1 = int(ann.get("x1", 0) * img_w)
                y1 = int(ann.get("y1", 0) * img_h)
                x2 = int(ann.get("x2", 0) * img_w)
                y2 = int(ann.get("y2", 0) * img_h)
                color_hex  = ann.get("color", "#FF0000")
                opacity    = float(ann.get("opacity", 1.0))
                line_width = int(ann.get("line_width", 3))
                brush_size = int(ann.get("brushSize", line_width))

                r, g, b      = self._hex_to_rgb(color_hex)
                stroke_color = (r, g, b, int(opacity * 255))
                fill_color   = (r, g, b, int(opacity * 255))
                bbox = [x1, y1, x2, y2]

                if shape == "rect":
                    draw.rectangle(bbox, outline=stroke_color, width=line_width)
                elif shape == "ellipse":
                    draw.ellipse(bbox, outline=stroke_color, width=line_width)
                elif shape == "fill_rect":
                    draw.rectangle(bbox, fill=fill_color, outline=stroke_color, width=line_width)
                elif shape == "fill_ellipse":
                    draw.ellipse(bbox, fill=fill_color, outline=stroke_color, width=line_width)
                elif shape == "line":
                    draw.line([x1, y1, x2, y2], fill=stroke_color, width=line_width)
                elif shape == "arrow":
                    self._draw_arrow(draw, x1, y1, x2, y2, stroke_color, line_width)
                elif shape == "brush":
                    points = ann.get("points", [])
                    if len(points) > 1:
                        coords = [(int(p[0] * img_w), int(p[1] * img_h)) for p in points]
                        for i in range(len(coords) - 1):
                            draw.line([coords[i], coords[i+1]], fill=stroke_color, width=brush_size)
                elif shape == "eraser":
                    pass

            if output_mode == "仅标注层":
                out_img = layer.convert("RGB")
            else:
                out_img = Image.alpha_composite(pil_img, layer).convert("RGB")

        out_np = np.array(out_img).astype(np.float32) / 255.0
        return (torch.from_numpy(out_np).unsqueeze(0),)

    def _draw_arrow(self, draw, x1, y1, x2, y2, color, width):
        """
        绘制箭头

        Time: 2026/02/27
        Author: Dapao
        """
        import math
        draw.line([x1, y1, x2, y2], fill=color, width=width)
        angle = math.atan2(y2 - y1, x2 - x1)
        head_len = max(width * 4, 12)
        for offset in [-0.4, 0.4]:
            hx = x2 - head_len * math.cos(angle + offset)
            hy = y2 - head_len * math.sin(angle + offset)
            draw.line([x2, y2, int(hx), int(hy)], fill=color, width=width)

    def _hex_to_rgb(self, hex_color: str):
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


NODE_CLASS_MAPPINGS = {
    "DapaoImageColorBoxNode": DapaoImageColorBoxNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageColorBoxNode": "🐭图像分色框选@炮老师的小课堂",
}

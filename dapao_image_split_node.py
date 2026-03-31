import torch
import comfy.utils
import folder_paths
from comfy import model_management
from spandrel import ModelLoader, ImageModelDescriptor


class DapaoImageSplitNode:
    """
    图像分割节点 - 按指定行列将图像切分为图像批次

    功能说明：
    - 支持自定义分割行数和列数
    - 支持将单张图像按网格切分
    - 如果输入本身是图像批次，会依次切分后合并输出
    - 支持可选的放大模型处理、缩放倍数和最长边限制
    - 输出结果为图像批次，方便后续继续处理

    Time: 2026/03/31
    Author: Dapao
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "🖼️ 输入图像": ("IMAGE", {
                    "tooltip": "需要进行网格分割的图像，可输入单张图或图像批次"
                }),
                "↕️ 分割行数": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 20,
                    "step": 1,
                    "tooltip": "纵向切成多少行，例如 2 表示 2 行"
                }),
                "↔️ 分割列数": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 20,
                    "step": 1,
                    "tooltip": "横向切成多少列，例如 3 表示 3 列"
                }),
                "🟢 启用模型放大": ("BOOLEAN", {
                    "default": False,
                    "label_on": "开启",
                    "label_off": "关闭",
                    "tooltip": "开启后，对每个切分小图使用放大模型增强"
                }),
                "🧠 放大模型": (folder_paths.get_filename_list("upscale_models"), {
                    "tooltip": "选择 ComfyUI 的放大模型"
                }),
                "🔍 放大倍数": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.1,
                    "max": 8.0,
                    "step": 0.1,
                    "tooltip": "基于切分后原图尺寸的最终缩放倍数；开启模型放大时，会在模型增强后自动调整到该目标倍数"
                }),
                "📏 最长边限制": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 8192,
                    "step": 8,
                    "tooltip": "0 表示不限制；大于 0 时，不管放大还是缩小，最终都会把单块图像最长边强制调整到该值"
                }),
                "🧪 缩放插值": (["lanczos", "bicubic", "bilinear", "area", "nearest-exact"], {
                    "default": "lanczos",
                    "tooltip": "普通缩放时使用的插值算法"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("🧩 分割图像批次",)
    FUNCTION = "split_image"
    CATEGORY = "🤖Dapao-Toolbox"

    def split_image(self, **kwargs):
        """
        按行列切分图像，并输出为图像批次。

        :param kwargs: 节点输入参数
        :return: 分割后的图像批次

        Time: 2026/03/31
        Author: Dapao
        """
        images = kwargs["🖼️ 输入图像"]
        rows = kwargs["↕️ 分割行数"]
        cols = kwargs["↔️ 分割列数"]
        enable_upscale = kwargs["🟢 启用模型放大"]
        upscale_model_name = kwargs["🧠 放大模型"]
        upscale_ratio = kwargs["🔍 放大倍数"]
        max_side = kwargs["📏 最长边限制"]
        upscale_method = kwargs["🧪 缩放插值"]

        if rows < 1 or cols < 1:
            raise ValueError("❌ 错误：分割行数和列数都必须大于 0！")

        batch_size, height, width, channels = images.shape
        if height < rows or width < cols:
            raise ValueError("❌ 错误：图像尺寸过小，无法按当前行列数进行分割！")

        tile_height = height // rows
        tile_width = width // cols
        if tile_height < 1 or tile_width < 1:
            raise ValueError("❌ 错误：当前分割行列过大，切分后的单块尺寸无效！")

        all_tiles = []

        # 🐅 逐张处理输入图像，再把所有分块合并成一个批次
        # 为保证输出能组成标准图像批次，所有分块尺寸必须完全一致
        for image_index in range(batch_size):
            image = images[image_index:image_index + 1]

            for row_index in range(rows):
                y_start = row_index * tile_height
                y_end = y_start + tile_height

                for col_index in range(cols):
                    x_start = col_index * tile_width
                    x_end = x_start + tile_width

                    tile = image[:, y_start:y_end, x_start:x_end, :channels]
                    all_tiles.append(tile)

        if not all_tiles:
            raise ValueError("❌ 错误：未成功生成任何分割图像！")

        output_batch = torch.cat(all_tiles, dim=0)

        if enable_upscale:
            upscale_model = self._load_upscale_model(upscale_model_name)
            output_batch = self._apply_upscale_model(upscale_model, output_batch)

        output_batch = self._apply_resize_controls(
            output_batch,
            original_width=tile_width,
            original_height=tile_height,
            upscale_ratio=upscale_ratio,
            max_side=max_side,
            upscale_method=upscale_method,
        )

        return (output_batch,)

    def _apply_resize_controls(self, images, original_width, original_height, upscale_ratio, max_side, upscale_method):
        """
        统一处理切块结果的最终尺寸控制。

        :param images: 图像批次
        :param original_width: 原始切块宽度
        :param original_height: 原始切块高度
        :param upscale_ratio: 目标缩放倍数
        :param max_side: 最长边限制
        :param upscale_method: 缩放算法
        :return: 处理后的图像批次

        Time: 2026/03/31
        Author: Dapao
        """
        target_width = max(1, round(original_width * upscale_ratio))
        target_height = max(1, round(original_height * upscale_ratio))

        if max_side > 0:
            if target_width >= target_height:
                scale = max_side / target_width
            else:
                scale = max_side / target_height

            target_width = max(1, round(target_width * scale))
            target_height = max(1, round(target_height * scale))

        current_height = images.shape[1]
        current_width = images.shape[2]

        if current_width == target_width and current_height == target_height:
            return images

        samples = images.movedim(-1, 1)
        resized = comfy.utils.common_upscale(samples, target_width, target_height, upscale_method, "disabled")
        return resized.movedim(1, -1).clamp(0.0, 1.0)

    def _load_upscale_model(self, model_name):
        """
        加载放大模型。

        :param model_name: 模型名称
        :return: 放大模型对象

        Time: 2026/03/31
        Author: Dapao
        """
        model_path = folder_paths.get_full_path_or_raise("upscale_models", model_name)
        state_dict = comfy.utils.load_torch_file(model_path, safe_load=True)

        if "module.layers.0.residual_group.blocks.0.norm1.weight" in state_dict:
            state_dict = comfy.utils.state_dict_prefix_replace(state_dict, {"module.": ""})

        upscale_model = ModelLoader().load_from_state_dict(state_dict).eval()

        if not isinstance(upscale_model, ImageModelDescriptor):
            raise ValueError("❌ 错误：当前选择的放大模型不是单图像放大模型！")

        return upscale_model

    def _apply_upscale_model(self, upscale_model, image):
        """
        使用放大模型处理图像批次。

        :param upscale_model: 放大模型
        :param image: 图像批次
        :return: 放大后的图像批次

        Time: 2026/03/31
        Author: Dapao
        """
        device = model_management.get_torch_device()

        memory_required = model_management.module_size(upscale_model.model)
        memory_required += (512 * 512 * 3) * image.element_size() * max(upscale_model.scale, 1.0) * 384.0
        memory_required += image.nelement() * image.element_size()
        model_management.free_memory(memory_required, device)

        upscale_model.to(device)
        in_img = image.movedim(-1, -3).to(device)

        tile = 512
        overlap = 32
        oom = True

        try:
            while oom:
                try:
                    steps = in_img.shape[0] * comfy.utils.get_tiled_scale_steps(
                        in_img.shape[3],
                        in_img.shape[2],
                        tile_x=tile,
                        tile_y=tile,
                        overlap=overlap,
                    )
                    pbar = comfy.utils.ProgressBar(steps)
                    scaled = comfy.utils.tiled_scale(
                        in_img,
                        lambda a: upscale_model(a),
                        tile_x=tile,
                        tile_y=tile,
                        overlap=overlap,
                        upscale_amount=upscale_model.scale,
                        pbar=pbar,
                    )
                    oom = False
                except Exception as error:
                    model_management.raise_non_oom(error)
                    tile //= 2
                    if tile < 128:
                        raise error
        finally:
            upscale_model.to("cpu")

        return torch.clamp(scaled.movedim(-3, -1), min=0.0, max=1.0)


NODE_CLASS_MAPPINGS = {
    "DapaoImageSplitNode": DapaoImageSplitNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageSplitNode": "🐅图像分割@炮老师的小课堂",
}

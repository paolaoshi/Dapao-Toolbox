import torch

MAX_OUTPUT_IMAGES = 999
DEFAULT_OUTPUT_IMAGES = 5


class DapaoImageUnpackNode:
    """
    🐬图像拆分节点 - 将图像批次或图像列表拆成多个单张图像输出

    功能说明：
    - 支持输入单个图像批次
    - 支持输入图像列表
    - 自动拆分成单张图像
    - 可自定义需要显示的单张输出数量
    - 配合前端扩展动态刷新输出口数量

    Time: 2026/03/31
    Author: Dapao
    """

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "🖼️ 输入图像": ("IMAGE", {
                    "tooltip": "可接单张图、图像批次，或来自列表流的图像输入"
                }),
                "🐬 单张输出数": ("INT", {
                    "default": DEFAULT_OUTPUT_IMAGES,
                    "min": 1,
                    "max": MAX_OUTPUT_IMAGES,
                    "step": 1,
                    "tooltip": "需要拆成多少个单张输出口，修改后点击前端按钮刷新输出口"
                }),
            }
        }

    RETURN_TYPES = tuple(["IMAGE"] * MAX_OUTPUT_IMAGES)
    RETURN_NAMES = tuple([f"图像_{index}" for index in range(1, MAX_OUTPUT_IMAGES + 1)])
    FUNCTION = "unpack_images"
    CATEGORY = "🤖Dapao-Toolbox"
    INPUT_IS_LIST = True

    def unpack_images(self, **kwargs):
        """
        将输入图像拆分成多个单张图像输出。

        :param kwargs: 节点输入参数
        :return: 多个单张图像输出

        Time: 2026/03/31
        Author: Dapao
        """
        image_inputs = kwargs.get("🖼️ 输入图像")
        if image_inputs is None:
            image_inputs = kwargs.get("🖼️ 图像")
        if image_inputs is None:
            image_inputs = []

        output_count = kwargs.get("🐬 单张输出数", [DEFAULT_OUTPUT_IMAGES])
        if isinstance(output_count, list):
            output_count = output_count[0] if output_count else DEFAULT_OUTPUT_IMAGES
        output_count = max(1, min(MAX_OUTPUT_IMAGES, int(output_count)))

        all_images = []
        self._collect_images(image_inputs, all_images)

        if not all_images:
            raise ValueError("❌ 错误：检测到节点已连接，但没有提取到可拆分图像，请刷新节点后再试一次！")

        placeholder = torch.zeros_like(all_images[0])
        outputs = []

        for output_index in range(MAX_OUTPUT_IMAGES):
            if output_index < output_count and output_index < len(all_images):
                outputs.append(all_images[output_index])
            else:
                outputs.append(placeholder)

        return tuple(outputs)

    def _collect_images(self, value, all_images):
        """
        递归提取图像，兼容图像批次、单张图像与列表输入。

        :param value: 任意输入值
        :param all_images: 输出收集列表

        Time: 2026/03/31
        Author: Dapao
        """
        if value is None:
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                self._collect_images(item, all_images)
            return

        if isinstance(value, torch.Tensor):
            if value.ndim == 4:
                for batch_index in range(value.shape[0]):
                    all_images.append(value[batch_index:batch_index + 1])
            elif value.ndim == 3:
                all_images.append(value.unsqueeze(0))


NODE_CLASS_MAPPINGS = {
    "DapaoImageUnpackNode": DapaoImageUnpackNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageUnpackNode": "🐬图像拆分@炮老师的小课堂",
}

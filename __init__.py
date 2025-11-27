# 导入节点
from .image_switch_node import ImageMultiSwitchNode
from .image_layout_node import ImageLayoutNode
from .make_image_batch_node import MakeImageBatchNode
from .image_aspect_ratio_node import ImageAspectRatioResizeNode
from .image_pad_direction_node import DapaoImagePadDirectionNode

# 前端资源目录
WEB_DIRECTORY = "./web"

# 节点注册配置
NODE_CLASS_MAPPINGS = {
    "DapaoImageMultiSwitchNode": ImageMultiSwitchNode,      # 多图片开关节点
    "DapaoImageLayoutNode": ImageLayoutNode,                # 图片排列节点
    "DapaoMakeImageBatchNode": MakeImageBatchNode,          # 制作图像批次节点
    "DapaoImageAspectRatioResizeNode": ImageAspectRatioResizeNode, # 按宽高比缩放节点
    "DapaoImagePadDirectionNode": DapaoImagePadDirectionNode, # 按方向外补画板
}

# 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageMultiSwitchNode": "多图片开关节点 🔢@炮老师的小课堂",
    "DapaoImageLayoutNode": "图片排列节点 📐@炮老师的小课堂",
    "DapaoMakeImageBatchNode": "制作图像批次 📦@炮老师的小课堂",
    "DapaoImageAspectRatioResizeNode": "按宽高比缩放 📐@炮老师的小课堂",
    "DapaoImagePadDirectionNode": "按方向外补画板 🖌️@炮老师的小课堂",
}

# 导出所有节点
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

# 导入节点
from .image_switch_node import ImageMultiSwitchNode
from .image_layout_node import ImageLayoutNode
from .make_image_batch_node import MakeImageBatchNode
from .image_aspect_ratio_node import ImageAspectRatioResizeNode
from .image_pad_direction_node import DapaoImagePadDirectionNode
from .prompt_brake_node import PromptBrakeNode
from .realtime_image_adjust_node import DapaoRealtimeImageAdjustNode
from .image_grid_stitcher_v2_node import ImageGridStitcherV2Node
from .dapao_batch_image_grid_node import DapaoBatchImageGrid
from .dapao_load_folder_images_node import DapaoLoadFolderImages
from .dapao_safe_save_image_node import DapaoSafeSaveImage
from .dapao_save_psd_node import DapaoSavePSD
from .dapao_image_ratio_limit_node import DapaoImageRatioLimitNode
from .dapao_batch_image_resize_node import DapaoBatchImageResize
from .dapao_image_compression_node import DapaoImageCompressionNode
from .dapao_random_prompt_line_extract_node import DapaoRandomPromptLineExtractNode
from .dapao_random_prompt_line_combine_node import DapaoRandomPromptLineCombineNode
from .dapao_smart_memory_optimizer_node import DapaoSmartMemoryOptimizerNode
from .dapao_image_color_box_node import DapaoImageColorBoxNode
from .dapao_image_split_node import DapaoImageSplitNode
from .dapao_image_unpack_node import DapaoImageUnpackNode
from .dapao_image_watermark_node import DapaoImageWatermarkNode

# 前端资源目录
WEB_DIRECTORY = "./web"

# 节点注册配置
NODE_CLASS_MAPPINGS = {
    "DapaoImageMultiSwitchNode": ImageMultiSwitchNode,      # 多图片开关节点
    "DapaoImageLayoutNode": ImageLayoutNode,                # 图片排列节点
    "DapaoMakeImageBatchNode": MakeImageBatchNode,          # 制作图像批次节点
    "DapaoImageAspectRatioResizeNode": ImageAspectRatioResizeNode, # 按宽高比缩放节点
    "DapaoImagePadDirectionNode": DapaoImagePadDirectionNode, # 按方向外补画板
    "DapaoPromptBrakeNode": PromptBrakeNode,                # 提示词刹车节点
    "DapaoRealtimeImageAdjustNode": DapaoRealtimeImageAdjustNode,     # 实时图像调整节点
    "DapaoImageGridStitcherV2Node": ImageGridStitcherV2Node,          # 图片网格拼接 V2
    "DapaoBatchImageGrid": DapaoBatchImageGrid,                       # 🐭批次图组合
    "DapaoLoadFolderImages": DapaoLoadFolderImages,                   # 🦁文件夹加载图像
    "DapaoSafeSaveImage": DapaoSafeSaveImage,                         # 😶‍🌫️安全保存图像
    "DapaoSavePSD": DapaoSavePSD,                                     # 🐋保存为PSD
    "DapaoImageRatioLimitNode": DapaoImageRatioLimitNode,             # 🫎图像比尺寸限定
    "DapaoBatchImageResize": DapaoBatchImageResize,                   # 🐣批量文件尺寸修改
    "DapaoImageCompressionNode": DapaoImageCompressionNode,           # 🦖画质无损压缩
    "DapaoRandomPromptLineExtractNode": DapaoRandomPromptLineExtractNode,
    "DapaoRandomPromptLineCombineNode": DapaoRandomPromptLineCombineNode,
    "DapaoSmartMemoryOptimizerNode": DapaoSmartMemoryOptimizerNode,
    "DapaoImageColorBoxNode": DapaoImageColorBoxNode,               # 🐭图像分色框选
    "DapaoImageSplitNode": DapaoImageSplitNode,                     # 🐅图像分割
    "DapaoImageUnpackNode": DapaoImageUnpackNode,                   # 🐬图像拆分
    "DapaoImageWatermarkNode": DapaoImageWatermarkNode,             # 🐥图像水印
}

# 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageMultiSwitchNode": "多图片开关节点 🔢@炮老师的小课堂",
    "DapaoImageLayoutNode": "图片排列节点 📐@炮老师的小课堂",
    "DapaoMakeImageBatchNode": "制作图像批次 📦@炮老师的小课堂",
    "DapaoImageAspectRatioResizeNode": "按宽高比缩放 📐@炮老师的小课堂",
    "DapaoImagePadDirectionNode": "按方向外补画板 🖌️@炮老师的小课堂",
    "DapaoPromptBrakeNode": "🦭提示词刹车@炮老师的小课堂",
    "DapaoRealtimeImageAdjustNode": "实时图像调整 🎨@炮老师的小课堂",
    "DapaoImageGridStitcherV2Node": "图片网格拼接 🧩@炮老师的小课堂",
    "DapaoBatchImageGrid": "🐭批次图组合@炮老师的小课堂",
    "DapaoLoadFolderImages": "🦁文件夹加载图像@炮老师的小课堂",
    "DapaoSafeSaveImage": "😶‍🌫️安全保存图像@炮老师的小课堂",
    "DapaoSavePSD": "🐋保存为PSD@炮老师的小课堂",
    "DapaoImageRatioLimitNode": "🫎图像比尺寸限定@炮老师的小课堂",
    "DapaoBatchImageResize": "🐣批量文件尺寸修改@炮老师的小课堂",
    "DapaoImageCompressionNode": "🦖画质无损压缩@炮老师的小课堂",
    "DapaoRandomPromptLineExtractNode": "🐧随机提示词行提取@炮老师的小课堂",
    "DapaoRandomPromptLineCombineNode": "🐧随机提示词行组合@炮老师的小课堂",
    "DapaoSmartMemoryOptimizerNode": "🐙显存丨内存智能优化@炮老师的小课堂",
    "DapaoImageColorBoxNode": "🐭图像分色框选@炮老师的小课堂",
    "DapaoImageSplitNode": "🐅图像分割@炮老师的小课堂",
    "DapaoImageUnpackNode": "🐬图像拆分@炮老师的小课堂",
    "DapaoImageWatermarkNode": "🐥图像水印@炮老师的小课堂",
}

# 导出所有节点
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

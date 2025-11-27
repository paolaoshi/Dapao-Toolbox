import torch
import torch.nn.functional as F

# 定义默认和最大输入数量
DEFAULT_IMAGES = 2  # 默认显示2个输入（前端会自动扩展）
MAX_IMAGES = 20     # 最多支持20个输入


class MakeImageBatchNode:
    """
    制作图像批次节点 - 将多个图像合并成一个批次
    
    功能说明：
    - 接收多个单独的图像输入
    - 将它们合并成一个图像批次（batch）
    - 支持最多20个图像输入
    - 智能动态输入：默认2个，连接后自动增加
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """定义节点的输入端口"""
        inputs = {
            "required": {},
            "optional": {}
        }
        
        # 添加默认数量的图像输入（使用 image1, image2... 命名）
        for i in range(1, DEFAULT_IMAGES + 1):
            inputs["optional"][f"📸 图像{i}"] = ("IMAGE", {
                "tooltip": f"第{i}张图像（可选）"
            })
        
        return inputs
    
    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("🖼️ 图像批次", "📊 图像数量")
    FUNCTION = "make_batch"
    CATEGORY = "🤖Dapao-Toolbox"
    
    def make_batch(self, **kwargs):
        """
        将多个图像合并成批次
        
        功能说明：
        - 收集所有输入的图像
        - 按顺序合并成一个批次
        - 返回合并后的批次和图像数量
        """
        
        # 收集所有输入的图像（检查所有可能的输入端口）
        images = []
        for i in range(1, MAX_IMAGES + 1):
            img = kwargs.get(f"📸 图像{i}", None)
            if img is not None:
                images.append(img)
        
        # 如果没有任何图像，返回错误
        if len(images) == 0:
            raise ValueError("❌ 错误: 至少需要提供一张图像！")
            
        # 统一图像尺寸（以第一张图像为准）
        target_h = images[0].shape[1]
        target_w = images[0].shape[2]
        processed_images = []
        
        for img in images:
            # 如果尺寸不一致，进行缩放
            if img.shape[1] != target_h or img.shape[2] != target_w:
                # 调整维度顺序为 [batch, channels, height, width] 以便 interpolate 使用
                img = img.permute(0, 3, 1, 2)
                # 缩放
                img = F.interpolate(img, size=(target_h, target_w), mode='bilinear', align_corners=False)
                # 恢复维度顺序为 [batch, height, width, channels]
                img = img.permute(0, 2, 3, 1)
            processed_images.append(img)
        
        # 合并所有图像成一个批次
        # 每个图像的shape是 [batch, height, width, channels]
        # 我们需要将它们沿着batch维度连接
        batch_images = torch.cat(processed_images, dim=0)
        
        # 返回批次和图像数量
        image_count = batch_images.shape[0]
        
        return (batch_images, image_count)


# ========== 节点注册配置 ==========
NODE_CLASS_MAPPINGS = {
    "DapaoMakeImageBatchNode": MakeImageBatchNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoMakeImageBatchNode": "制作图像批次 📦@炮老师的小课堂"
}

import torch
import numpy as np
import io
from PIL import Image

class DapaoImageCompressionNode:
    """
    画质无损压缩节点
    提供高质量的图像压缩功能，支持批量处理
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "输入图像"}),
                "quality": ("INT", {
                    "default": 90, 
                    "min": 1, 
                    "max": 100, 
                    "step": 1, 
                    "tooltip": "压缩质量 (1-100)，数值越高画质越好，建议85-95"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("🖼️ 图像",)
    FUNCTION = "compress_image"
    CATEGORY = "🤖Dapao-Toolbox"

    def compress_image(self, image, quality):
        result_images = []
        
        # 处理 batch
        for i in range(image.shape[0]):
            img_tensor = image[i]
            img_pil = self.tensor2pil(img_tensor)
            
            # 压缩处理
            # 使用 BytesIO 在内存中模拟保存 JPEG 过程
            buffer = io.BytesIO()
            
            # 转换模式，确保兼容性
            if img_pil.mode == 'RGBA':
                # 如果需要保持透明度，JPEG不支持RGBA，通常转RGB或混合背景
                # 这里为了压缩效果，如果用户意图是JPEG压缩，通常是RGB
                # 但为了通用性，如果原图是RGBA，我们先尝试转RGB（JPEG标准）
                # 或者如果用户想保留透明度但压缩体积，应该用PNG压缩（WebP等）
                # 按照参考竞品逻辑（JPEG压缩），通常转RGB
                img_pil = img_pil.convert('RGB')
            elif img_pil.mode != 'RGB':
                img_pil = img_pil.convert('RGB')
                
            # 保存到 buffer，应用压缩参数
            # optimize=True: 启用编码优化
            # subsampling=0: 关闭色度二次采样 (4:4:4)，保持最高颜色质量
            img_pil.save(buffer, format="JPEG", quality=quality, optimize=True, subsampling=0)
            
            # 从 buffer 重新读取
            buffer.seek(0)
            compressed_img_pil = Image.open(buffer)
            
            # 转回 Tensor
            result_images.append(self.pil2tensor(compressed_img_pil))
            
        # 合并 batch
        if len(result_images) > 1:
            return (torch.cat(result_images, dim=0),)
        else:
            return (result_images[0],)

    def tensor2pil(self, image):
        return Image.fromarray(np.clip(255. * image.cpu().numpy(), 0, 255).astype(np.uint8))

    def pil2tensor(self, image):
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

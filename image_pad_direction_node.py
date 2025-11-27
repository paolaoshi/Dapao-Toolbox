import torch
import torch.nn.functional as F

class DapaoImagePadDirectionNode:
    """
    按方向外补画板节点
    
    功能说明：
    - 支持按上下左右四个方向进行图像外补(Pad)
    - 支持像素和百分比两种单位
    - 支持自动调整尺寸以满足整除要求
    - 支持遮罩(Mask)同步处理及边缘羽化
    - 支持自定义填充颜色
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "📸 图像": ("IMAGE",),
                "📏 单位": (["像素", "百分比"], {
                    "default": "像素",
                    "tooltip": "选择外补数值的单位，像素=绝对值，百分比=相对于原图尺寸"
                }),
                "⬅️ 左": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 10000, 
                    "step": 1,
                    "tooltip": "向左延伸的距离"
                }),
                "➡️ 右": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 10000, 
                    "step": 1,
                    "tooltip": "向右延伸的距离"
                }),
                "⬆️ 上": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 10000, 
                    "step": 1,
                    "tooltip": "向上延伸的距离"
                }),
                "⬇️ 下": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 10000, 
                    "step": 1,
                    "tooltip": "向下延伸的距离"
                }),
                "🎨 填充颜色": (["custom", "black", "white", "red", "green", "blue", "yellow", "cyan", "magenta"], {
                    "default": "black",
                    "tooltip": "选择外补区域的填充颜色，custom=使用HEX自定义颜色"
                }),
                "🌈 填充色HEX": ("STRING", {
                    "default": "#000000",
                    "multiline": False,
                    "tooltip": "自定义填充颜色的HEX值 (例如 #FF0000)"
                }),
                "🌫️ 羽化": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 500, 
                    "step": 1,
                    "tooltip": "遮罩边缘的羽化半径"
                }),
                "🔢 整除数": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 1024, 
                    "step": 1,
                    "tooltip": "确保输出尺寸是该数值的倍数（0表示不限制）。如有余数会自动增加到右侧/下方。"
                }),
            },
            "optional": {
                "😷 遮罩": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "INT")
    RETURN_NAMES = ("🖼️ 图像", "😷 遮罩", "❓ 是否外补")
    FUNCTION = "pad_image"
    CATEGORY = "🤖Dapao-Toolbox"

    def pad_image(self, **kwargs):
        # 参数获取
        image = kwargs.get("📸 图像")
        mask = kwargs.get("😷 遮罩")
        unit = kwargs.get("📏 单位", "像素")
        left = kwargs.get("⬅️ 左", 0)
        right = kwargs.get("➡️ 右", 0)
        top = kwargs.get("⬆️ 上", 0)
        bottom = kwargs.get("⬇️ 下", 0)
        fill_color_name = kwargs.get("🎨 填充颜色", "black")
        fill_color_hex = kwargs.get("🌈 填充色HEX", "#000000")
        feather = kwargs.get("🌫️ 羽化", 0)
        modulo = kwargs.get("🔢 整除数", 0)

        # 处理 Mask 初始状态
        if mask is None:
            # 如果没有输入 mask，创建一个全黑 mask (表示保留原图)
            # mask shape: [B, H, W]
            mask = torch.zeros((image.shape[0], image.shape[1], image.shape[2]), dtype=torch.float32, device=image.device)
        else:
            # 确保 mask 维度匹配
            if len(mask.shape) == 2:
                mask = mask.unsqueeze(0).repeat(image.shape[0], 1, 1)
            elif mask.shape[0] != image.shape[0]:
                # 如果 batch 不匹配，尝试广播
                mask = mask.repeat(image.shape[0], 1, 1)[:image.shape[0]]

        B, H, W, C = image.shape
        
        # 计算 Padding 数值
        if unit == "百分比":
            left = int(W * left / 100)
            right = int(W * right / 100)
            top = int(H * top / 100)
            bottom = int(H * bottom / 100)
        
        # 整除数调整 (Modulo)
        new_w = W + left + right
        new_h = H + top + bottom
        
        if modulo > 0:
            rem_w = new_w % modulo
            if rem_w != 0:
                right += (modulo - rem_w)
            
            rem_h = new_h % modulo
            if rem_h != 0:
                bottom += (modulo - rem_h)

        # 检查是否需要外补
        if left == 0 and right == 0 and top == 0 and bottom == 0:
            return (image, mask, 0)
        
        # 解析颜色
        color_map = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255)
        }

        rgb_color = (0, 0, 0) # default black
        if fill_color_name == "custom":
            try:
                # 解析 HEX
                hex_str = fill_color_hex.lstrip('#')
                if len(hex_str) == 6:
                    rgb_color = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
                elif len(hex_str) == 3:
                    rgb_color = tuple(int(hex_str[i] + hex_str[i], 16) for i in (0, 1, 2))
            except:
                print(f"Warning: Invalid hex code {fill_color_hex}, using black.")
        else:
            rgb_color = color_map.get(fill_color_name, (0, 0, 0))
            
        # 归一化颜色到 0-1
        fill_r = rgb_color[0] / 255.0
        fill_g = rgb_color[1] / 255.0
        fill_b = rgb_color[2] / 255.0

        # 执行图像 Padding (使用构建新画板的方法以支持颜色)
        # image is [B, H, W, C]
        target_h = H + top + bottom
        target_w = W + left + right
        
        # 创建背景张量
        new_image = torch.zeros((B, target_h, target_w, C), dtype=image.dtype, device=image.device)
        
        # 填充颜色
        new_image[:, :, :, 0] = fill_r
        new_image[:, :, :, 1] = fill_g
        new_image[:, :, :, 2] = fill_b
        
        # 将原图复制到新画板
        # top:top+H, left:left+W
        new_image[:, top:top+H, left:left+W, :] = image

        # 执行 Mask Padding
        # Mask: [B, H, W] -> Add Dim [B, 1, H, W]
        mask_expanded = mask.unsqueeze(1)
        # 外补区域填充 1.0 (表示需要重绘/Inpaint)
        # 这里依然可以使用 F.pad，因为 mask 是单通道且 padding value 统一
        mask_padded = F.pad(mask_expanded, (left, right, top, bottom), mode='constant', value=1.0)
        
        # 羽化处理 (Feathering)
        if feather > 0:
            # 使用高斯模糊处理 Mask
            k_size = 2 * feather + 1
            sigma = float(feather) / 2.0
            mask_padded = self.gaussian_blur(mask_padded, k_size, sigma)
        
        result_mask = mask_padded.squeeze(1)

        return (new_image, result_mask, 1)

    def gaussian_blur(self, x, k_size, sigma):
        """
        使用 PyTorch 实现简单的二维高斯模糊
        """
        # 创建 1D 高斯核
        x_coord = torch.arange(k_size, dtype=x.dtype, device=x.device) - (k_size - 1) / 2
        kernel_1d = torch.exp(- (x_coord**2) / (2 * sigma**2))
        kernel_1d = kernel_1d / kernel_1d.sum()
        
        # Reshape 为 2D 卷积核: [Out, In, H, W] -> [1, 1, K, 1] 和 [1, 1, 1, K]
        k_x = kernel_1d.view(1, 1, 1, k_size)
        k_y = kernel_1d.view(1, 1, k_size, 1)
        
        # 填充大小
        pad_size = k_size // 2
        
        # 分离卷积 (Separable Convolution) 提速
        # 1. 水平方向卷积 (W)
        # 使用 replicate 填充以保持边缘数值
        x = F.pad(x, (pad_size, pad_size, 0, 0), mode='replicate')
        x = F.conv2d(x, k_x)
        
        # 2. 垂直方向卷积 (H)
        x = F.pad(x, (0, 0, pad_size, pad_size), mode='replicate')
        x = F.conv2d(x, k_y)
        
        return x

import torch
import numpy as np
from PIL import Image, ImageDraw
import math
import os
from pathlib import Path


class ImageLayoutNode:
    """
    图片自动排列节点 - 左侧大图，右侧网格排列
    
    功能说明：
    - 基准图片放在左侧，显示为大图
    - 批次图片在右侧按照网格自动排列
    - 支持自动计算最优行列数或手动设置
    - 美化的参数界面，使用emoji图标
    """
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """节点每次都重新计算"""
        return float("NaN")
    
    @classmethod
    def INPUT_TYPES(cls):
        """定义节点的输入端口"""
        return {
            "required": {
                # 📸 基准图片
                "📸 基准图片": ("IMAGE", {
                    "tooltip": "基准图片，作为主图显示"
                }),
                # 📁 使用文件夹
                "📁 使用文件夹": ("BOOLEAN", {
                    "default": False,
                    "label_on": "启用 ✓",
                    "label_off": "禁用 ✗",
                    "tooltip": "启用后使用文件夹路径加载批次图片，禁用则使用批次图片输入端口"
                }),
                # 📂 图片文件夹路径
                "📂 图片文件夹路径": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "批次图片文件夹路径（需启用'使用文件夹'开关）"
                }),
                # 🎯 排列方向
                "🎯 排列方向": (["左右排列", "上下排列", "左上排列", "右上排列"], {
                    "default": "左右排列",
                    "tooltip": "左右=基准图在左, 上下=基准图在上, 左上=基准图左上角, 右上=基准图右上角"
                }),
                # 📐 基准图尺寸模式
                "📐 基准图尺寸模式": (["默认", "自定义最长边"], {
                    "default": "默认",
                    "tooltip": "默认=自动计算尺寸, 自定义最长边=指定最长边像素"
                }),
                # 📏 基准图最长边
                "📏 基准图最长边": ("INT", {
                    "default": 512,
                    "min": 256,
                    "max": 2048,
                    "step": 64,
                    "tooltip": "基准图最长边的像素值（自定义模式下生效）"
                }),
                # 📐 布局模式
                "📐 布局模式": (["自动", "固定列数", "固定行数"], {
                    "default": "自动",
                    "tooltip": "自动=自动计算最优布局, 固定列数=固定列数, 固定行数=固定行数"
                }),
                # 📊 列数
                "📊 列数": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "tooltip": "右侧网格的列数（固定列数模式下生效）"
                }),
                # 📏 行数
                "📏 行数": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "tooltip": "右侧网格的行数（固定行数模式下生效）"
                }),
                # 🔍 小图尺寸
                "🔍 小图尺寸": ("INT", {
                    "default": 256,
                    "min": 64,
                    "max": 1024,
                    "step": 64,
                    "tooltip": "右侧批次图片的尺寸（正方形）"
                }),
                # 📏 间距
                "📏 间距": ("INT", {
                    "default": 10,
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "tooltip": "图片之间的间距（像素）"
                }),
                # 🎨 缩放模式
                "🎨 缩放模式": (["适应", "裁剪", "拉伸"], {
                    "default": "适应",
                    "tooltip": "适应=保持比例适应, 裁剪=裁剪填充, 拉伸=拉伸填充"
                }),
                # 🌈 背景颜色
                "🌈 背景颜色": (["白色", "黑色", "灰色", "透明"], {
                    "default": "白色",
                    "tooltip": "背景颜色"
                }),
            },
            "optional": {
                # 🖼️ 批次图片（可选）
                "🖼️ 批次图片": ("IMAGE", {
                    "tooltip": "批次图片，按网格排列（需禁用'使用文件夹'开关）"
                }),
                # 🔢 最大批次数
                "🔢 最大批次数": ("INT", {
                    "default": 20,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "最大显示的批次图片数量"
                }),
                # 🖼️ 添加边框
                "🖼️ 添加边框": ("BOOLEAN", {
                    "default": False,
                    "label_on": "显示 ✓",
                    "label_off": "隐藏 ✗",
                    "tooltip": "是否为图片添加边框"
                }),
                # 🎨 边框颜色
                "🎨 边框颜色": (["黑色", "白色", "灰色", "红色", "蓝色"], {
                    "default": "黑色",
                    "tooltip": "边框颜色"
                }),
                # 📏 边框宽度
                "📏 边框宽度": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "tooltip": "边框宽度（像素）"
                })
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT")
    RETURN_NAMES = ("🖼️ 排列图像", "ℹ️ 布局信息", "📊 总图片数", "📐 网格尺寸")
    FUNCTION = "create_layout"
    CATEGORY = "🤖Dapao-Toolbox"
    
    def create_layout(self, **kwargs):
        """
        创建图片排列布局 - 支持四种排列方向
        
        排列方向：
        - 左右排列：基准图在左，批次图在右
        - 上下排列：基准图在上，批次图在下
        - 左上排列：基准图在左上角，批次图环绕
        - 右上排列：基准图在右上角，批次图环绕
        """
        
        # 获取参数
        base_image = kwargs.get("📸 基准图片")
        use_folder = kwargs.get("📁 使用文件夹", False)
        folder_path = kwargs.get("📂 图片文件夹路径", "")
        batch_images = kwargs.get("🖼️ 批次图片", None)
        arrangement = kwargs.get("🎯 排列方向", "左右排列")
        base_size_mode = kwargs.get("📐 基准图尺寸模式", "默认")
        base_max_size = kwargs.get("📏 基准图最长边", 512)
        layout_mode = kwargs.get("📐 布局模式", "自动")
        columns = kwargs.get("📊 列数", 2)
        rows = kwargs.get("📏 行数", 2)
        small_size = kwargs.get("🔍 小图尺寸", 256)
        spacing = kwargs.get("📏 间距", 10)
        batch_resize_mode = kwargs.get("🎨 缩放模式", "适应")
        background_color = kwargs.get("🌈 背景颜色", "白色")
        max_batch_images = kwargs.get("🔢 最大批次数", 20)
        add_border = kwargs.get("🖼️ 添加边框", False)
        border_color = kwargs.get("🎨 边框颜色", "黑色")
        border_width = kwargs.get("📏 边框宽度", 2)
        
        # 映射中文选项到英文
        layout_mode_map = {"自动": "auto", "固定列数": "fixed_columns", "固定行数": "fixed_rows"}
        resize_mode_map = {"适应": "fit", "裁剪": "crop", "拉伸": "stretch"}
        bg_color_map = {"白色": "white", "黑色": "black", "灰色": "gray", "透明": "transparent"}
        border_color_map = {"黑色": "black", "白色": "white", "灰色": "gray", "红色": "red", "蓝色": "blue"}
        arrangement_map = {"左右排列": "left_right", "上下排列": "top_bottom", "左上排列": "top_left", "右上排列": "top_right"}
        
        layout_mode_en = layout_mode_map.get(layout_mode, "auto")
        resize_mode_en = resize_mode_map.get(batch_resize_mode, "fit")
        bg_color_en = bg_color_map.get(background_color, "white")
        border_color_en = border_color_map.get(border_color, "black")
        arrangement_en = arrangement_map.get(arrangement, "left_right")
        
        try:
            # 1. 转换基准图片
            base_pil = self.tensor_to_pil(base_image[0])
            
            # 2. 根据开关获取批次图片
            batch_pils = []
            if use_folder:
                # 启用文件夹：从文件夹读取图片
                if folder_path and os.path.exists(folder_path):
                    batch_pils = self.load_images_from_folder(folder_path, max_batch_images)
                else:
                    # 文件夹路径无效
                    error_img = Image.new('RGB', (800, 200), (255, 100, 100))
                    draw = ImageDraw.Draw(error_img)
                    draw.text((10, 80), f"❌ 错误: 文件夹路径无效或不存在！\n路径: {folder_path}", fill="white")
                    error_tensor = self.pil_to_tensor(error_img)
                    return (error_tensor, f"❌ 错误: 文件夹路径无效", 1, 0)
            else:
                # 禁用文件夹：使用输入端口的批次图片
                if batch_images is not None:
                    batch_pils = [self.tensor_to_pil(img) for img in batch_images]
                else:
                    # 没有提供批次图片
                    error_img = Image.new('RGB', (800, 200), (255, 100, 100))
                    draw = ImageDraw.Draw(error_img)
                    draw.text((10, 80), "❌ 错误: 请连接批次图片输入端口！", fill="white")
                    error_tensor = self.pil_to_tensor(error_img)
                    return (error_tensor, "❌ 错误: 没有批次图片", 1, 0)
            
            # 3. 限制批次图片数量
            if len(batch_pils) > max_batch_images:
                batch_pils = batch_pils[:max_batch_images]
            
            batch_count = len(batch_pils)
            
            # 如果没有批次图片，返回错误
            if batch_count == 0:
                error_img = Image.new('RGB', (800, 200), (255, 100, 100))
                draw = ImageDraw.Draw(error_img)
                draw.text((10, 80), "❌ 错误: 没有批次图片！请提供批次图片或文件夹路径", fill="white")
                error_tensor = self.pil_to_tensor(error_img)
                return (error_tensor, "❌ 错误: 没有批次图片", 1, 0)
            
            # 3. 计算右侧网格的行列数
            if layout_mode_en == "auto":
                # 自动计算最优行列数（尽量接近正方形网格）
                grid_cols = math.ceil(math.sqrt(batch_count))
                grid_rows = math.ceil(batch_count / grid_cols)
            elif layout_mode_en == "fixed_columns":
                # 固定列数，自动计算行数
                grid_cols = columns
                grid_rows = math.ceil(batch_count / grid_cols)
            elif layout_mode_en == "fixed_rows":
                # 固定行数，自动计算列数
                grid_rows = rows
                grid_cols = math.ceil(batch_count / grid_rows)
            else:
                grid_cols = 2
                grid_rows = math.ceil(batch_count / 2)
            
            # 确保至少有1行1列
            grid_cols = max(1, grid_cols)
            grid_rows = max(1, grid_rows)
            
            # 4. 计算批次图片网格区域的尺寸
            grid_width = grid_cols * small_size + (grid_cols - 1) * spacing
            grid_height = grid_rows * small_size + (grid_rows - 1) * spacing
            
            # 5. 计算基准图片的尺寸
            if base_size_mode == "自定义最长边":
                # 自定义最长边模式
                base_aspect_ratio = base_pil.width / base_pil.height
                if base_pil.width > base_pil.height:
                    # 宽度是最长边
                    base_width = base_max_size
                    base_height = int(base_max_size / base_aspect_ratio)
                else:
                    # 高度是最长边
                    base_height = base_max_size
                    base_width = int(base_max_size * base_aspect_ratio)
            else:
                # 默认模式：根据排列方向自动计算
                base_aspect_ratio = base_pil.width / base_pil.height
                if arrangement_en in ["left_right", "top_left", "top_right"]:
                    # 左右排列：基准图高度与网格相同
                    base_height = grid_height
                    base_width = int(base_height * base_aspect_ratio)
                else:
                    # 上下排列：基准图宽度与网格相同
                    base_width = grid_width
                    base_height = int(base_width / base_aspect_ratio)
            
            # 调整基准图片尺寸
            base_resized = base_pil.resize((base_width, base_height), Image.Resampling.LANCZOS)
            
            # 6. 根据排列方向计算总画布尺寸和位置
            if arrangement_en == "left_right":
                # 左右排列：基准图在左，批次图在右
                canvas_width = base_width + spacing + grid_width
                canvas_height = max(base_height, grid_height)
                base_x = 0
                base_y = (canvas_height - base_height) // 2
                grid_start_x = base_width + spacing
                grid_start_y = (canvas_height - grid_height) // 2
            elif arrangement_en == "top_bottom":
                # 上下排列：基准图在上，批次图在下
                canvas_width = max(base_width, grid_width)
                canvas_height = base_height + spacing + grid_height
                base_x = (canvas_width - base_width) // 2
                base_y = 0
                grid_start_x = (canvas_width - grid_width) // 2
                grid_start_y = base_height + spacing
            elif arrangement_en == "top_left":
                # 左上排列：基准图在左上角
                canvas_width = base_width + spacing + grid_width
                canvas_height = max(base_height, grid_height)
                base_x = 0
                base_y = 0
                grid_start_x = base_width + spacing
                grid_start_y = 0
            elif arrangement_en == "top_right":
                # 右上排列：基准图在右上角
                canvas_width = base_width + spacing + grid_width
                canvas_height = max(base_height, grid_height)
                base_x = grid_width + spacing
                base_y = 0
                grid_start_x = 0
                grid_start_y = 0
            else:
                # 默认左右排列
                canvas_width = base_width + spacing + grid_width
                canvas_height = max(base_height, grid_height)
                base_x = 0
                base_y = (canvas_height - base_height) // 2
                grid_start_x = base_width + spacing
                grid_start_y = (canvas_height - grid_height) // 2
            
            # 7. 创建背景画布
            bg_color = self.get_background_color(bg_color_en)
            canvas = Image.new('RGB', (canvas_width, canvas_height), bg_color)
            
            # 8. 粘贴基准图片
            if add_border:
                bordered_base = self.add_image_border(base_resized, border_color_en, border_width)
                canvas.paste(bordered_base, (base_x, base_y))
            else:
                canvas.paste(base_resized, (base_x, base_y))
            
            # 9. 排列批次图片
            
            for i, batch_img in enumerate(batch_pils):
                # 计算当前图片在网格中的位置
                row = i // grid_cols
                col = i % grid_cols
                
                # 如果超出网格范围，停止添加
                if row >= grid_rows:
                    break
                
                # 根据缩放模式调整批次图片
                if resize_mode_en == "crop":
                    # 裁剪模式：居中裁剪填充正方形
                    batch_resized = self.resize_to_square_crop(batch_img, small_size)
                elif resize_mode_en == "fit":
                    # 适应模式：保持比例，添加背景
                    batch_resized = self.resize_to_square_fit(batch_img, small_size, bg_color)
                elif resize_mode_en == "stretch":
                    # 拉伸模式：直接拉伸到正方形
                    batch_resized = self.resize_to_square_stretch(batch_img, small_size)
                else:
                    # 默认使用适应模式
                    batch_resized = self.resize_to_square_fit(batch_img, small_size, bg_color)
                
                # 计算粘贴位置
                x = grid_start_x + col * (small_size + spacing)
                y = grid_start_y + row * (small_size + spacing)
                
                # 粘贴图片
                if add_border:
                    bordered_batch = self.add_image_border(batch_resized, border_color_en, border_width)
                    canvas.paste(bordered_batch, (x, y))
                else:
                    canvas.paste(batch_resized, (x, y))
            
            # 10. 转换回tensor
            result_tensor = self.pil_to_tensor(canvas)
            
            # 11. 生成布局信息
            source_info = f"文件夹({os.path.basename(folder_path)})" if use_folder else "输入端口"
            layout_info = (
                f"🎯 排列: {arrangement} | "
                f"📐 布局: {layout_mode} | "
                f"📸 基准图: {base_width}×{base_height} | "
                f"📊 网格: {grid_rows}行×{grid_cols}列 | "
                f"🖼️ 批次: {batch_count}张({source_info}) | "
                f"📏 画布: {canvas_width}×{canvas_height}"
            )
            
            total_images = 1 + batch_count  # 1张基准图 + N张批次图
            grid_size_value = grid_rows * 100 + grid_cols  # 例如: 3行2列 = 302
            
            return (result_tensor, layout_info, total_images, grid_size_value)
            
        except Exception as e:
            # 错误处理：返回错误提示图片
            import traceback
            error_msg = f"错误: {str(e)}\n{traceback.format_exc()}"
            print(f"[ImageLayoutNode] {error_msg}")
            
            error_img = Image.new('RGB', (800, 600), (255, 100, 100))
            draw = ImageDraw.Draw(error_img)
            draw.text((10, 10), f"❌ 布局生成失败:\n{str(e)}", fill="white")
            
            error_tensor = self.pil_to_tensor(error_img)
            return (error_tensor, f"❌ 错误: {str(e)}", 0, 0)
    
    def tensor_to_pil(self, tensor):
        """将tensor转换为PIL图片"""
        # tensor格式: [H, W, C]
        if len(tensor.shape) == 4:
            tensor = tensor[0]  # 移除batch维度
        
        # 确保值在0-1范围内
        tensor = torch.clamp(tensor, 0, 1)
        
        # 转换为numpy并调整到0-255范围
        np_image = (tensor.cpu().numpy() * 255).astype(np.uint8)
        
        # 转换为PIL图片
        if np_image.shape[2] == 3:  # RGB
            return Image.fromarray(np_image, 'RGB')
        elif np_image.shape[2] == 4:  # RGBA
            return Image.fromarray(np_image, 'RGBA')
        else:
            # 灰度图转RGB
            return Image.fromarray(np_image[:,:,0], 'L').convert('RGB')
    
    def pil_to_tensor(self, pil_image):
        """将PIL图片转换为tensor"""
        # 转换为RGB模式
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # 转换为numpy数组
        np_image = np.array(pil_image).astype(np.float32) / 255.0
        
        # 转换为tensor并添加batch维度
        tensor = torch.from_numpy(np_image).unsqueeze(0)  # [1, H, W, C]
        
        return tensor
    
    def resize_to_square_crop(self, image, target_size):
        """
        将图片调整为正方形 - 裁剪模式
        保持宽高比，居中裁剪（会裁掉部分内容）
        """
        original_width, original_height = image.size
        
        # 计算缩放比例（填充满正方形）
        scale = max(target_size / original_width, target_size / original_height)
        
        # 按比例缩放
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 居中裁剪为正方形
        left = (new_width - target_size) // 2
        top = (new_height - target_size) // 2
        cropped = resized.crop((left, top, left + target_size, top + target_size))
        
        return cropped
    
    def resize_to_square_fit(self, image, target_size, bg_color):
        """
        将图片调整为正方形 - 适应模式
        保持宽高比，不裁剪，添加背景填充（推荐）
        """
        original_width, original_height = image.size
        
        # 计算缩放比例（适应正方形内）
        scale = min(target_size / original_width, target_size / original_height)
        
        # 按比例缩放
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 创建正方形背景
        background = Image.new('RGB', (target_size, target_size), bg_color)
        
        # 居中粘贴缩放后的图片
        offset_x = (target_size - new_width) // 2
        offset_y = (target_size - new_height) // 2
        background.paste(resized, (offset_x, offset_y))
        
        return background
    
    def resize_to_square_stretch(self, image, target_size):
        """
        将图片调整为正方形 - 拉伸模式
        直接拉伸到目标尺寸（会变形）
        """
        return image.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    def add_image_border(self, image, border_color, border_width):
        """
        给图片添加边框
        """
        # 获取边框颜色
        color_map = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "gray": (128, 128, 128),
            "red": (255, 0, 0),
            "blue": (0, 0, 255)
        }
        border_rgb = color_map.get(border_color, (0, 0, 0))
        
        # 创建带边框的新图片
        new_width = image.width + 2 * border_width
        new_height = image.height + 2 * border_width
        
        # 创建边框背景
        bordered = Image.new('RGB', (new_width, new_height), border_rgb)
        
        # 将原图粘贴到中心
        bordered.paste(image, (border_width, border_width))
        
        return bordered
    
    def get_background_color(self, color_name):
        """获取背景颜色"""
        colors = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "gray": (128, 128, 128),
            "transparent": (255, 255, 255)  # PIL不支持真正的透明，用白色代替
        }
        return colors.get(color_name, (255, 255, 255))
    
    def load_images_from_folder(self, folder_path, max_count):
        """
        从文件夹加载图片
        
        参数：
        - folder_path: 文件夹路径
        - max_count: 最大加载数量
        
        返回：
        - PIL图片列表
        """
        images = []
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
        
        try:
            # 获取文件夹中的所有文件
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                print(f"[ImageLayoutNode] 文件夹不存在: {folder_path}")
                return images
            
            # 遍历文件夹中的文件
            files = sorted(folder.iterdir())
            for file_path in files:
                if len(images) >= max_count:
                    break
                
                # 检查文件扩展名
                if file_path.suffix.lower() in supported_formats:
                    try:
                        img = Image.open(file_path)
                        # 转换为RGB模式
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        images.append(img)
                        print(f"[ImageLayoutNode] 加载图片: {file_path.name}")
                    except Exception as e:
                        print(f"[ImageLayoutNode] 加载图片失败 {file_path.name}: {str(e)}")
                        continue
            
            print(f"[ImageLayoutNode] 从文件夹加载了 {len(images)} 张图片")
            return images
            
        except Exception as e:
            print(f"[ImageLayoutNode] 读取文件夹失败: {str(e)}")
            return images


# ========== 节点注册配置 ==========
NODE_CLASS_MAPPINGS = {
    "DapaoImageLayoutNode": ImageLayoutNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageLayoutNode": "图片排列节点 📐@炮老师的小课堂"
}

# 定义默认和最大输入数量
DEFAULT_IMAGES = 2  # 默认显示2个输入（前端会自动扩展）
MAX_IMAGES = 20     # 最多支持20个输入

class ImageMultiSwitchNode:
    """
    多图片开关节点 - 支持多图片输入和智能选择
    
    功能说明：
    - 支持最多20张图片输入
    - 使用编号选择器快速切换图片
    - 支持自动检测有效图片并跳过空图片
    - 美化的参数显示界面
    """
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """节点每次都重新计算"""
        return float("NaN")
    
    @classmethod
    def INPUT_TYPES(cls):
        """定义节点的输入端口"""
        inputs = {
            "required": {
                # 🎯 编号选择器
                "🎯 编号": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": MAX_IMAGES,
                    "step": 1,
                    "tooltip": "选择要输出的图片编号（1-20）"
                }),
            },
            "optional": {
                # 🎨 功能选项
                "⏭️ 跳过空图片": ("BOOLEAN", {
                    "default": True,
                    "label_on": "启用 ✓",
                    "label_off": "禁用 ✗",
                    "tooltip": "如果选中的图片为空，自动使用下一张有效图片"
                }),
                "🔄 循环模式": ("BOOLEAN", {
                    "default": False,
                    "label_on": "启用 ✓",
                    "label_off": "禁用 ✗",
                    "tooltip": "当索引超出范围时，循环回到第一张图片"
                }),
            }
        }
        
        # 只添加默认数量的图片输入端口
        # 使用 image1, image2... 命名（从1开始）
        for i in range(1, DEFAULT_IMAGES + 1):
            inputs["optional"][f"image{i}"] = ("IMAGE", {
                "tooltip": f"第{i}张输入图片（可选）"
            })
        
        return inputs
    
    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT")
    RETURN_NAMES = ("🖼️ 图像", "ℹ️ 信息", "🔢 索引", "📊 总数")
    FUNCTION = "switch_image"
    CATEGORY = "🤖Dapao-Toolbox"
    
    def switch_image(self, **kwargs):
        """
        多图片切换的主要逻辑函数
        
        参数说明：
        - kwargs: 包含所有输入参数的字典
        
        返回值：
        - 选中的图片
        - 信息文本
        - 实际选中的索引号（整数，从0开始）
        - 总图片数量
        """
        
        # 获取控制参数
        select_index = kwargs.get("🎯 编号", 1)
        skip_empty = kwargs.get("⏭️ 跳过空图片", True)
        loop_mode = kwargs.get("🔄 循环模式", False)
        
        # 收集所有输入的图片（检查所有可能的输入端口）
        images = []
        for i in range(1, MAX_IMAGES + 1):
            img = kwargs.get(f"image{i}", None)
            if img is not None:
                images.append((i, img))  # 保存编号和图片
        
        # 如果没有任何图片输入，返回错误信息
        if not images:
            error_msg = "❌ 错误: 没有输入任何图片！"
            return (None, error_msg, 0, 0)
        
        total_images = len(images)
        
        # 直接使用编号查找对应的图片
        selected_image = kwargs.get(f"image{select_index}", None)
        selected_idx = select_index
        
        # 如果选中的图片不存在，需要处理
        if selected_image is None:
            if loop_mode and total_images > 0:
                # 循环模式：使用取模找到有效的图片
                # 将编号映射到实际存在的图片列表
                index = ((select_index - 1) % total_images)
                selected_idx, selected_image = images[index]
            else:
                # 非循环模式：使用边界限制
                if select_index < images[0][0]:
                    # 小于最小编号，使用第一张
                    selected_idx, selected_image = images[0]
                else:
                    # 大于最大编号，使用最后一张
                    selected_idx, selected_image = images[-1]
        
        # 如果启用了跳过空图片功能
        if selected_image is None and skip_empty and total_images > 0:
            # 找到第一张有效的图片
            for idx, img in images:
                if img is not None:
                    selected_idx, selected_image = idx, img
                    break
        
        # 生成信息文本
        info_lines = [
            f"✅ 输出: image{selected_idx}",
            f"📊 总数: {total_images}",
            f"🎯 请求: {select_index}",
        ]
        
        if loop_mode:
            info_lines.append("🔄 循环: 开")
        
        if skip_empty:
            info_lines.append("⏭️ 跳过: 开")
        
        info_text = " | ".join(info_lines)
        
        # 返回结果
        return (selected_image, info_text, selected_idx, total_images)


# ========== 节点注册配置 ==========
# 这部分代码告诉ComfyUI有哪些节点可以使用

# 节点类映射：将节点的内部名称映射到类
NODE_CLASS_MAPPINGS = {
    "DapaoImageMultiSwitchNode": ImageMultiSwitchNode, # 多图片开关节点
}

# 节点显示名称映射：定义节点在ComfyUI界面上显示的名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoImageMultiSwitchNode": "多图片开关节点 🔢@炮老师的小课堂",
}

---
description: 
---

---
description: auto_execution_mode: 3
auto_execution_mode: 3
---

项目规则 参考

# Dapao-Toolbox项目规则

## 角色定义
你是一个经验丰富的 Python 开发者，专注于开发 ComfyUI 自定义节点

## 代码规范

### 1. 节点开发规范
- 所有节点必须包含完整的类定义，包括 `INPUT_TYPES`、`RETURN_TYPES`、`RETURN_NAMES`、`FUNCTION`、`CATEGORY`
- 节点分类统一使用 `CATEGORY = "🤖Dapao-Toolbox`
- 必须在文件末尾注册节点到 `NODE_CLASS_MAPPINGS` 和 `NODE_DISPLAY_NAME_MAPPINGS`

### 2. 图像处理规范
- 输入图像的张量形状：`[B, H, W, C]`（批次、高度、宽度、通道）
- 输入遮罩的张量形状：`[B, H, W]`
- 确保图像值范围在 0-1 之间（float32）
- 使用 `pil2tensor()` 和 `tensor2pil()` 进行格式转换

### 3、路径与文件管理规范（核心重构 - 解决模型加载 Bug）

确保节点在不同用户的电脑（Windows/Linux/Mac）上均可运行：
禁止绝对路径：严禁出现如 C:/Users/... 或 /home/user/... 的硬编码路径。
使用 ComfyUI 原生路径工具：
引用模型时，必须使用 folder_paths 模块。
例如：获取 checkpoint 路径使用 folder_paths.get_full_path("checkpoints", ckpt_name)。
列出模型列表使用 folder_paths.get_filename_list("checkpoints")。
插件内部资源引用：
如果需要引用当前插件文件夹内的文件（如默认配置、图标），必须使用相对路径锚定：
<PYTHON>
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")
模型下载逻辑：
下载模型时，目标路径应动态获取 folder_paths.models_dir，不可硬编码。
必须检查文件是否已存在，避免重复下载。  

### 安全与隐私规范（核心重构 - 防止 API 泄露）
- 这是最高优先级规则，任何涉及敏感信息的代码必须遵循：

- 零持久化原则：严禁在代码中将 API Key、Secret 或 Token 写入到任何会被 Git 追踪的 JSON/YAML/PY 文件中。
- 配置分离模式：
- 模板文件：项目仅提供 config.json.example（仅包含空值或占位符），并强制提交到仓库。
- 本地配置：实际的 config.json 必须被添加到 .gitignore 中，由用户在本地生成。
- 代码逻辑：节点加载时，优先读取环境变量 -> 其次读取 config.json -> 最后回退到节点 Widget 输入。
- 输入优先：建议将 API Key 设计为节点的 INPUT_TYPES 中的 STRING 类型（设置 multiline: false），由用户在 ComfyUI 界面输入，不依赖本地文件。
- Git 忽略：在创建项目结构时，必须生成 .gitignore 文件，并明确包含：
- <TEXT>
config.json
api_keys.yaml
*.env
__pycache__/


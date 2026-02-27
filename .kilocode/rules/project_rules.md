# Dapao-Toolbox 项目规则

## 1. 节点开发规范

- 所有节点必须包含完整的类定义，包括 `INPUT_TYPES`、`RETURN_TYPES`、`RETURN_NAMES`、`FUNCTION`、`CATEGORY`
- 节点分类统一使用 `CATEGORY = "🤖Dapao-Toolbox"`
- 必须在文件末尾注册节点到 `NODE_CLASS_MAPPINGS` 和 `NODE_DISPLAY_NAME_MAPPINGS`

## 2. 图像处理规范

- 输入图像的张量形状：`[B, H, W, C]`（批次、高度、宽度、通道）
- 输入遮罩的张量形状：`[B, H, W]`
- 确保图像值范围在 0-1 之间（float32）
- 使用 `pil2tensor()` 和 `tensor2pil()` 进行格式转换

## 3. 路径与文件管理规范

- 模型路径：严禁使用绝对路径。所有模型（Checkpoint, VAE, Lora）的加载与下载路径，必须通过 ComfyUI 的 `folder_paths` 模块动态获取
- 资源引用：插件内文件（配置、图标）需使用相对路径锚定
- 下载逻辑：目标路径不可硬编码，下载前必须校验文件是否存在

## 4. 安全与隐私（最高优先级）

- 零持久化原则：严禁将 API Key/Token 写入任何 Git 追踪的文件中
- 配置分离模式：
  - 仅提交 `config.json.example`（空值模板）
  - 实际 `config.json` 必须由用户本地生成，并强制加入 `.gitignore`
- 读取优先级：环境变量 > 本地 Config > 节点 Widget 输入（推荐）
- `.gitignore` 必须包含：`config.json`、`api_keys.yaml`、`*.env`、`__pycache__/`

## 5. 代码注释规范

```python
class ExampleNode:
    """
    节点功能简要描述

    Time: 2026/xx/xx
    Author: Dapao
    """

    def execute(self, param1):
        """
        方法详细描述

        :param param1: 参数说明
        :return: 返回值说明

        Time: 2026/xx/xx
        Author: Dapao
        """
        pass
```

## 6. 语言规范

- 所有回复、代码注释、文档均使用**简体中文**
- 操作系统环境：Windows 11

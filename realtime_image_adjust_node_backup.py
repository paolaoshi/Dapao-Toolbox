import torch
import numpy as np
from PIL import Image, ImageEnhance
import torch.nn.functional as F
import base64
import io
from server import PromptServer
from threading import Event
from aiohttp import web
import traceback

# 全局存储节点数据
node_data = {}


class RealtimeImageAdjustNode:
    """
    实时图像调整节点
    
    功能说明：
    - 调整图片色彩饱和度
    - 调整明暗对比度
    - 调整亮度
    - 图像尺寸缩放（保持或拉伸比例）
    - 支持实时预览
    - 手动应用调整
    """
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """支持实时预览 - 参数改变时重新计算"""
        return float("NaN")
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": "输入图像"
                }),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("adjusted_image",)
    FUNCTION = "adjust_image"
    CATEGORY = "dapao"
    OUTPUT_NODE = True  # 标记为输出节点，支持实时预览
    
    def adjust_image(self, image, unique_id):
        """
        调整图像 - 等待前端实时调整完成
        """
        try:
            node_id = str(unique_id)  # 确保是字符串
            event = Event()
            
            # 存储节点数据和事件
            node_data[node_id] = {
                "event": event,
                "result": None,
                "shape": image.shape
            }
            
            print(f"[实时图像调整] 节点ID: {node_id}, 类型: {type(node_id)}")
            
            # 准备预览图像（转换为base64）
            preview_image = (torch.clamp(image.clone(), 0, 1) * 255).cpu().numpy().astype(np.uint8)[0]
            pil_image = Image.fromarray(preview_image)
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            try:
                # 通过WebSocket发送预览图像到前端
                PromptServer.instance.send_sync("realtime_image_adjust_update", {
                    "node_id": node_id,
                    "image_data": f"data:image/png;base64,{base64_image}",
                    "shape": list(image.shape)
                })
                
                print(f"[实时图像调整] 节点 {node_id} 发送预览图像，等待用户点击'应用调整'按钮...")
                
                # 无限等待，直到用户点击"应用调整"按钮
                event.wait()
                
                print(f"[实时图像调整] 节点 {node_id} 用户已应用调整，继续执行")
                
                # 获取调整后的结果
                result_image = node_data[node_id]["result"]
                del node_data[node_id]
                
                print(f"[实时图像调整] 节点 {node_id} 接收到调整结果")
                return (result_image if result_image is not None else image,)
                
            except Exception as e:
                print(f"[实时图像调整] 节点 {node_id} 处理失败: {str(e)}")
                traceback.print_exc()
                if node_id in node_data:
                    del node_data[node_id]
                return (image,)
            
        except Exception as e:
            print(f"[实时图像调整] 执行失败: {str(e)}")
            traceback.print_exc()
            if node_id in node_data:
                del node_data[node_id]
            return (image,)


# 注册API路由 - 接收前端调整后的数据
@PromptServer.instance.routes.post("/realtime_image_adjust/apply")
async def apply_realtime_adjust(request):
    """
    接收前端发送的调整后图像数据
    """
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))  # 确保是字符串
        adjusted_data = data.get("adjusted_data")
        
        print(f"[实时图像调整] 接收到节点 {node_id} 的调整数据, 类型: {type(node_id)}")
        print(f"[实时图像调整] 当前存储的节点ID列表: {list(node_data.keys())}")
        
        if node_id not in node_data:
            print(f"[实时图像调整] 警告: 节点 {node_id} 数据不存在（可能已处理）")
            return web.json_response({"success": False, "error": "节点数据不存在或已处理"})
        
        # 检查是否已经处理过
        if node_data[node_id].get("processed", False):
            print(f"[实时图像调整] 警告: 节点 {node_id} 已经处理过，忽略重复请求")
            return web.json_response({"success": False, "error": "已经处理过"})
        
        try:
            node_info = node_data[node_id]
            
            if isinstance(adjusted_data, list):
                # 从请求中获取调整后的宽高
                adjusted_width = data.get("width")
                adjusted_height = data.get("height")
                
                batch, orig_height, orig_width, channels = node_info["shape"]
                
                # 使用调整后的尺寸
                if adjusted_width and adjusted_height:
                    height = adjusted_height
                    width = adjusted_width
                else:
                    height = orig_height
                    width = orig_width
                
                print(f"[实时图像调整] 接收数据: 原始{orig_width}x{orig_height} -> 调整后{width}x{height}")
                
                # 将像素数据转换为tensor
                expected_len = height * width * 4
                if len(adjusted_data) >= expected_len:
                    rgba_array = np.array(adjusted_data[:expected_len], dtype=np.uint8).reshape(height, width, 4)
                    rgb_array = rgba_array[:, :, :3]
                    tensor_image = torch.from_numpy(rgb_array / 255.0).float().unsqueeze(0)
                    node_info["result"] = tensor_image
                    print(f"[实时图像调整] 成功转换图像数据: {tensor_image.shape}")
                else:
                    print(f"[实时图像调整] 错误: 数据长度不足 (需要{expected_len}, 实际{len(adjusted_data)})")
                    # 即使数据不足也要触发Event，避免卡住
                    node_info["result"] = None
            
            # 标记为已处理，防止重复请求
            node_info["processed"] = True
            
            # 触发事件，让Python端继续执行
            node_info["event"].set()
            
            print(f"[实时图像调整] 节点 {node_id} 处理完成，Event已触发")
            return web.json_response({"success": True})
            
        except Exception as e:
            print(f"[实时图像调整] 处理数据失败: {str(e)}")
            traceback.print_exc()
            if node_id in node_data and "event" in node_data[node_id]:
                node_data[node_id]["event"].set()
            return web.json_response({"success": False, "error": str(e)})
    
    except Exception as e:
        print(f"[实时图像调整] 请求处理失败: {str(e)}")
        traceback.print_exc()
        return web.json_response({"success": False, "error": str(e)})


# 节点注册配置
WEB_DIRECTORY = "web"

NODE_CLASS_MAPPINGS = {
    "RealtimeImageAdjustNode": RealtimeImageAdjustNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RealtimeImageAdjustNode": "实时图像调整 🎨@炮老师的小课堂"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

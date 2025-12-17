import time
from server import PromptServer
from aiohttp import web
import uuid

# 全局缓存
BRAKE_CACHE = {}

class PromptBrakeNode:
    """
    提示词刹车节点
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True, "multiline": True, "label": "📝 提示词(Input)"}), 
                "⏱️ 超时时间(秒)": ("INT", {"default": 60, "min": 5, "max": 3600, "step": 1, "display": "number"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("📝 最终提示词",)
    FUNCTION = "run_brake"
    CATEGORY = "🤖Dapao-Toolbox" # 修正分类到带机器人Emoji的组

    def run_brake(self, text, unique_id=None, prompt=None, extra_pnginfo=None, **kwargs):
        # 获取中文参数
        timeout = kwargs.get("⏱️ 超时时间(秒)", 60)
        
        my_id = unique_id
        print(f"[PromptBrake] Node {my_id} started.")
        
        # 1. 注册状态
        BRAKE_CACHE[my_id] = {
            "status": "waiting",
            "text": text,
        }
        
        # 2. 发送事件给前端 (前端据此弹窗或更新UI)
        PromptServer.instance.send_sync("dapao.brake.start", {
            "node_id": my_id,
            "text": text,
            "timeout": timeout
        })
        
        # 3. 阻塞循环
        start_time = time.time()
        final_text = text
        
        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    print(f"[PromptBrake] Timeout.")
                    break
                
                state = BRAKE_CACHE.get(my_id)
                if state and state["status"] == "done":
                    # 从缓存获取最新的文本（可能是用户修改过的）
                    final_text = state["text"] 
                    print(f"[PromptBrake] Confirmed.")
                    break
                
                time.sleep(0.1)
                
        finally:
            if my_id in BRAKE_CACHE:
                del BRAKE_CACHE[my_id]
            
            PromptServer.instance.send_sync("dapao.brake.end", {
                "node_id": my_id
            })

        return (final_text,)

# API 路由
def setup_routes():
    try:
        routes = PromptServer.instance.routes
        # 防止重复注册
        for route in routes:
            if route.method == "POST" and route.path == "/dapao/brake/update":
                return

        @routes.post("/dapao/brake/update")
        async def update_brake_status(request):
            try:
                data = await request.json()
                node_id = data.get("node_id")
                new_text = data.get("text")
                action = data.get("action")
                
                if node_id in BRAKE_CACHE:
                    BRAKE_CACHE[node_id]["text"] = new_text
                    BRAKE_CACHE[node_id]["status"] = "done"
                    return web.json_response({"status": "success"})
                else:
                    return web.json_response({"status": "error"}, status=404)
            except Exception as e:
                return web.json_response({"status": "error"}, status=500)
                
    except Exception as e:
        print(f"[Dapao] API Error: {e}")

setup_routes()

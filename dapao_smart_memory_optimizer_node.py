import gc

import psutil
import torch
from comfy.comfy_types import IO


class DapaoSmartMemoryOptimizerNode:
    DESCRIPTION = "用途：显存/内存智能优化（预留显存、低内存/低显存时卸载模型、清空缓存、GC）。\n放置位置：建议放在工作流最前面；或在加载大模型/高分辨率采样前再放一个。\n直通用法：把“🔌 任意输入”接在你想触发的位置，输出端继续接回原流程，即可精确控制本节点何时执行。\n信息展示：运行后信息会直接显示在节点里（无需接信息输出端口）。\n参数说明：\n- 预留显存GB：写入 ComfyUI 的预留显存设置，给系统/其它程序留显存；越大越稳，但可用显存越少。\n- 内存安全余量GB：RAM 可用低于此值时触发“卸载全部模型 + 清理”。\n- 显存安全余量GB：VRAM 可用低于此值时触发“卸载部分模型占用 + 清理”。\n- 低内存时卸载全部模型：更激进，适合爆内存/频繁切图场景。\n- 运行时清空缓存：每次运行都做一次缓存清理，能缓解碎片但可能略慢。\n- 强制GC：强制 Python 垃圾回收，配合清理更彻底但可能卡一下。\n如何判断生效：看节点内显示的“动作=…”和“预留显存=…”，以及运行前后 RAM/VRAM 可用数值变化。"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "✅ 启用": ("BOOLEAN", {"default": True, "tooltip": "总开关；关闭时不做任何优化，仅输出状态"}),
                "🐙 预留显存GB": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 256.0, "step": 0.1, "tooltip": "预留给系统/其它程序的显存(GB)。越大越稳，但可用显存越少"}),
                "🧠 内存安全余量GB": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 512.0, "step": 0.5, "tooltip": "RAM可用低于此值(GB)时触发“卸载全部模型+清理”"}),
                "🧠 显存安全余量GB": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 256.0, "step": 0.1, "tooltip": "VRAM可用低于此值(GB)时触发“卸载部分模型占用+清理”；0表示不启用该规则"}),
                "🧹 低内存时卸载全部模型": ("BOOLEAN", {"default": True, "tooltip": "当RAM不足时卸载所有已加载模型，回收更彻底但会触发后续重新加载"}),
                "🧽 运行时清空缓存": ("BOOLEAN", {"default": True, "tooltip": "每次运行都清理一次缓存，缓解碎片，但可能略慢"}),
                "🧯 强制GC": ("BOOLEAN", {"default": True, "tooltip": "强制Python垃圾回收(gc.collect)，可能更彻底但会有短暂停顿"}),
            },
            "optional": {
                "🔌 任意输入": (IO.ANY, {"tooltip": "任意类型直通输入：把它接在你想触发优化的环节中间"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = (IO.ANY,)
    RETURN_NAMES = ("🔌 任意输出",)
    FUNCTION = "optimize"
    CATEGORY = "🤖Dapao-Toolbox/🧠性能优化"
    OUTPUT_NODE = True

    def _format_bytes(self, n: int) -> str:
        if n is None:
            return "0"
        if n >= 1024**3:
            return f"{n / (1024**3):.2f}GB"
        return f"{n / (1024**2):.0f}MB"

    def optimize(self, **kwargs):
        import comfy.model_management as model_management

        any_in = kwargs.get("🔌 任意输入", None)
        unique_id = kwargs.get("unique_id", kwargs.get("UNIQUE_ID", None))

        enabled = bool(kwargs.get("✅ 启用", True))
        reserve_vram_gb = float(kwargs.get("🐙 预留显存GB", 0.6))
        min_ram_gb = float(kwargs.get("🧠 内存安全余量GB", 4.0))
        min_vram_gb = float(kwargs.get("🧠 显存安全余量GB", 0.0))
        unload_on_low_ram = bool(kwargs.get("🧹 低内存时卸载全部模型", True))
        clear_cache = bool(kwargs.get("🧽 运行时清空缓存", True))
        force_gc = bool(kwargs.get("🧯 强制GC", True))

        dev = model_management.get_torch_device()
        vm = psutil.virtual_memory()
        ram_total = int(vm.total)
        ram_avail = int(vm.available)

        old_reserved = int(getattr(model_management, "EXTRA_RESERVED_VRAM", 0))

        actions = []
        if not enabled:
            info = (
                f"状态=关闭 | 设备={dev} | "
                f"RAM可用={self._format_bytes(ram_avail)}/{self._format_bytes(ram_total)} | "
                f"预留显存={self._format_bytes(old_reserved)}"
            )
            if unique_id is not None:
                from server import PromptServer
                PromptServer.instance.send_sync("dapao.memopt.info", {"node_id": int(unique_id), "info": info})
            return {"ui": {"dapao_info": info, "text": [info]}, "result": (any_in,)}

        model_management.EXTRA_RESERVED_VRAM = max(0, int(reserve_vram_gb * (1024**3)))
        if model_management.EXTRA_RESERVED_VRAM != old_reserved:
            actions.append(f"预留显存:{self._format_bytes(old_reserved)}→{self._format_bytes(model_management.EXTRA_RESERVED_VRAM)}")

        if clear_cache:
            model_management.soft_empty_cache()
            actions.append("清空缓存")

        if unload_on_low_ram and min_ram_gb > 0:
            threshold_ram = int(min_ram_gb * (1024**3))
            if ram_avail < threshold_ram:
                model_management.unload_all_models()
                model_management.free_memory(1e30, torch.device("cpu"))
                if force_gc:
                    gc.collect()
                model_management.soft_empty_cache()
                actions.append("低内存卸载模型")

        vram_total = 0
        vram_free = 0
        if hasattr(dev, "type") and dev.type not in ("cpu", "mps"):
            try:
                vram_total = int(model_management.get_total_memory(dev))
                # 获取更详细的内存信息：Total_Free = OS_Free + Torch_Reserved_Free
                mem_free_total, mem_free_torch = model_management.get_free_memory(dev, torch_free_too=True)
                # 计算真实的 OS 层面剩余显存（Task Manager 看到的空闲）
                os_free = mem_free_total - mem_free_torch
            except Exception:
                vram_total = 0
                mem_free_total = 0
                os_free = 0

            reserved_bytes = int(getattr(model_management, "EXTRA_RESERVED_VRAM", 0))
            
            # 策略升级：双重检查
            # 1. 检查 Torch 自身占用是否越界 (Self-Discipline)
            #    如果 (Torch已占用 + 预留) > 总显存，说明 ComfyUI 占用了本该预留的空间，必须吐出来
            torch_reserved_bytes = 0
            try:
                torch_reserved_bytes = torch.cuda.memory_reserved(dev)
            except:
                pass
            
            # 2. 检查系统层面是否真的拥挤 (System Pressure)
            #    虽然 os_free 有时虚高，但如果它真的很低，那肯定要卸载
            
            should_unload_reserved = False
            
            # 判定 A: Torch 自身占用过高
            if reserved_bytes > 0 and vram_total > 0:
                max_allowed_torch = vram_total - reserved_bytes
                if torch_reserved_bytes > max_allowed_torch:
                    should_unload_reserved = True
            
            # 判定 B: 系统剩余显存不足 (辅助判断)
            if reserved_bytes > 0 and os_free < reserved_bytes:
                should_unload_reserved = True
                
            if should_unload_reserved:
                # 1. 先尝试轻量级清空
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                
                # 重新检查
                try:
                    torch_reserved_bytes = torch.cuda.memory_reserved(dev)
                    mem_free_total, mem_free_torch = model_management.get_free_memory(dev, torch_free_too=True)
                    os_free = mem_free_total - mem_free_torch
                except:
                    pass
                    
                # 再次确认是否还需要卸载模型
                still_need_unload = False
                if vram_total > 0 and torch_reserved_bytes > (vram_total - reserved_bytes):
                    still_need_unload = True
                if os_free < reserved_bytes:
                    still_need_unload = True
                    
                if still_need_unload:
                    # 计算需要释放多少：
                    # 目标是让 torch_reserved <= (vram_total - reserved_bytes)
                    # 或者 os_free >= reserved_bytes
                    # 这里直接给一个足够大的值让 ComfyUI 尽力释放，或者按差值释放
                    # 为了保险，直接尝试释放预留的大小，或者更多
                    
                    target_free = reserved_bytes
                    # 如果是因为 Torch 占太多，算出超额部分
                    if vram_total > 0:
                        excess = torch_reserved_bytes - (vram_total - reserved_bytes)
                        if excess > 0:
                            target_free = max(target_free, excess)
                    
                    model_management.free_memory(target_free, dev)
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                    actions.append("按预留卸载模型")
                    
                    # 更新状态
                    try:
                        mem_free_total, mem_free_torch = model_management.get_free_memory(dev, torch_free_too=True)
                        torch_reserved_bytes = torch.cuda.memory_reserved(dev)
                    except:
                        pass

            if min_vram_gb > 0:
                need_free = int(min_vram_gb * (1024**3))
                # 逻辑可用显存 = 总显存 - Torch占用 - 预留
                # 或者 = mem_free_total - reserved_bytes (ComfyUI视角)
                # 为了更安全，我们用更保守的计算：
                # 假设 Torch 还能申请到的最大值是 (vram_total - reserved_bytes - torch_reserved_bytes)
                # 但 mem_free_total 已经包含了 torch_reserved 里未使用的部分
                # 所以还是用 mem_free_total - reserved_bytes 比较符合 ComfyUI 定义
                
                vram_free_effective = max(0, mem_free_total - reserved_bytes)
                if vram_free_effective < need_free:
                    # 需要腾出 (need_free + reserved_bytes) 才能保证安全
                    model_management.free_memory(need_free + reserved_bytes, dev)
                    torch.cuda.empty_cache()
                    actions.append("低显存卸载模型")

        if force_gc and not unload_on_low_ram:
            gc.collect()
            actions.append("GC")

        vm2 = psutil.virtual_memory()
        ram_avail2 = int(vm2.available)
        if hasattr(dev, "type") and dev.type not in ("cpu", "mps"):
            try:
                reserved_bytes2 = int(getattr(model_management, "EXTRA_RESERVED_VRAM", 0))
                mem_free_total2, mem_free_torch2 = model_management.get_free_memory(dev, torch_free_too=True)
                os_free2 = mem_free_total2 - mem_free_torch2
                torch_reserved2 = torch.cuda.memory_reserved(dev)
                
                # VRAM可用(逻辑)：ComfyUI 还能用多少 (扣除预留)
                vram_free_logical = max(0, mem_free_total2 - reserved_bytes2)
                
                # Torch占用：当前 Torch 实际申请了多少
                torch_usage_str = self._format_bytes(torch_reserved2)
                
            except Exception:
                mem_free_total2 = 0
                os_free2 = 0
                vram_free_logical = 0
                torch_reserved2 = 0
                torch_usage_str = "0"
        else:
            mem_free_total2 = 0
            os_free2 = 0
            vram_free_logical = 0
            torch_reserved2 = 0
            torch_usage_str = "0"
  
        action_text = "；".join(actions) if actions else "无"
        info = (
            f"动作={action_text} | 设备={dev} | "
            f"RAM可用={self._format_bytes(ram_avail2)}/{self._format_bytes(ram_total)} | "
            f"VRAM可用(逻辑)={self._format_bytes(vram_free_logical)} | "
            f"系统剩余={self._format_bytes(os_free2)} | "
            f"Torch占用={torch_usage_str} | "
            f"预留设置={self._format_bytes(int(model_management.EXTRA_RESERVED_VRAM))}"
        )
        if unique_id is not None:
            from server import PromptServer
            PromptServer.instance.send_sync("dapao.memopt.info", {"node_id": int(unique_id), "info": info})
        return {"ui": {"dapao_info": info, "text": [info]}, "result": (any_in,)}


NODE_CLASS_MAPPINGS = {
    "DapaoSmartMemoryOptimizerNode": DapaoSmartMemoryOptimizerNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DapaoSmartMemoryOptimizerNode": "🐙显存丨内存智能优化@炮老师的小课堂",
}

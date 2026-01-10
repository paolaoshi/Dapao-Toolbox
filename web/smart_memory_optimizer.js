import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "Dapao.SmartMemoryOptimizer",

    async setup() {
        api.addEventListener("dapao.memopt.info", (event) => {
            const { node_id, info } = event.detail || {};
            if (node_id == null) return;

            const nodeIdNum = typeof node_id === "number" ? node_id : parseInt(String(node_id), 10);
            const node =
                app.graph.getNodeById(nodeIdNum) ??
                app.graph.getNodeById(String(node_id)) ??
                app.graph._nodes?.find(n => n && (n.id == node_id));
            if (!node || !node.dapaoMemoryInfoWidget) return;

            const text = String(info ?? "");
            node.dapaoMemoryInfoWidget.value = text || "（无信息）";
            app.graph.setDirtyCanvas(true, true);
        });

        api.addEventListener("executed", (event) => {
            const payload = event?.detail || {};
            const nodeId = payload.node ?? payload.node_id ?? payload.id ?? payload?.detail?.node ?? payload?.detail?.node_id;
            const output = payload.output ?? payload.outputs ?? payload?.detail?.output ?? payload?.detail?.outputs;
            if (nodeId == null) return;

            const nodeIdNum = typeof nodeId === "number" ? nodeId : parseInt(String(nodeId), 10);
            const node =
                app.graph.getNodeById(nodeIdNum) ??
                app.graph.getNodeById(String(nodeId)) ??
                app.graph._nodes?.find(n => n && (n.id == nodeId));
            if (!node || !node.dapaoMemoryInfoWidget) return;

            const ui = output?.ui ?? output?.output?.ui ?? output?.outputs?.ui ?? {};
            const raw = ui.dapao_info ?? ui.text ?? ui.dapao_info_text ?? "";
            const text = Array.isArray(raw) ? raw.join("\n") : String(raw ?? "");

            if (text) node.dapaoMemoryInfoWidget.value = text;
            app.graph.setDirtyCanvas(true, true);
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "DapaoSmartMemoryOptimizerNode") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            const wrapper = ComfyWidgets["STRING"](this, "ℹ️ 运行信息", ["STRING", { multiline: true }], app);
            this.dapaoMemoryInfoWidget = wrapper.widget;
            this.dapaoMemoryInfoWidget.serialize = false;
            this.dapaoMemoryInfoWidget.value = "等待运行...";

            if (this.dapaoMemoryInfoWidget?.inputEl) {
                this.dapaoMemoryInfoWidget.inputEl.readOnly = true;
                this.dapaoMemoryInfoWidget.inputEl.style.height = "90px";
            }

            this.setSize([520, 360]);
            return r;
        };
    },
});

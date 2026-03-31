import { app } from "../../scripts/app.js";

const NODE_NAME = "DapaoImageWatermarkNode";
const NODE_TITLE = "🐥图像水印@炮老师的小课堂";

app.registerExtension({
    name: "Dapao.ImageWatermark",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME && nodeData.display_name !== NODE_TITLE) {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        const onConfigure = nodeType.prototype.onConfigure;

        const applyNodeTitle = function () {
            this.title = NODE_TITLE;
            if (typeof this.setDirtyCanvas === "function") {
                this.setDirtyCanvas(true, true);
            }
        };

        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
            applyNodeTitle.call(this);
            return result;
        };

        nodeType.prototype.onConfigure = function () {
            const result = onConfigure ? onConfigure.apply(this, arguments) : undefined;
            setTimeout(() => applyNodeTitle.call(this), 10);
            return result;
        };
    }
});

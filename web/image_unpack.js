import { app } from "../../scripts/app.js";

const MAX_OUTPUT_IMAGES = 999;
const DEFAULT_OUTPUT_IMAGES = 5;

app.registerExtension({
    name: "Dapao.ImageUnpack",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "DapaoImageUnpackNode" && nodeData.display_name !== "🐬图像拆分@炮老师的小课堂") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        const onConfigure = nodeType.prototype.onConfigure;

        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            this.updateDapaoOutputs = function () {
                const countWidget = this.widgets?.find(widget => widget.name === "🐬 单张输出数");
                let outputCount = Number(countWidget?.value ?? DEFAULT_OUTPUT_IMAGES);
                if (!Number.isFinite(outputCount)) {
                    outputCount = DEFAULT_OUTPUT_IMAGES;
                }
                outputCount = Math.max(1, Math.min(MAX_OUTPUT_IMAGES, Math.round(outputCount)));

                if (countWidget) {
                    countWidget.value = outputCount;
                }

                const currentOutputs = Array.isArray(this.outputs) ? [...this.outputs] : [];
                for (let index = currentOutputs.length - 1; index >= 0; index--) {
                    const output = currentOutputs[index];
                    if (output?.name?.startsWith("图像_")) {
                        this.removeOutput(index);
                    }
                }

                for (let index = 1; index <= outputCount; index++) {
                    this.addOutput(`图像_${index}`, "IMAGE");
                }

                if (typeof this.computeSize === "function") {
                    const newSize = this.computeSize();
                    if (Array.isArray(newSize) && newSize.length >= 2) {
                        this.setSize(newSize);
                    }
                }

                this.setDirtyCanvas(true, true);
            };

            const hasUpdateButton = this.widgets?.some(widget => widget.name === "🔄 刷新输出口");
            if (!hasUpdateButton) {
                this.addWidget("button", "🔄 刷新输出口", "", () => {
                    this.updateDapaoOutputs();
                }, {
                    tooltip: "根据当前的单张输出数，刷新右侧输出口数量"
                });
            }

            setTimeout(() => {
                this.updateDapaoOutputs();
            }, 10);

            return result;
        };

        nodeType.prototype.onConfigure = function () {
            const result = onConfigure ? onConfigure.apply(this, arguments) : undefined;

            setTimeout(() => {
                if (typeof this.updateDapaoOutputs === "function") {
                    this.updateDapaoOutputs();
                }
            }, 10);

            return result;
        };
    }
});

import { app } from "../../scripts/app.js";

// 为制作图像批次节点添加动态输入功能
app.registerExtension({
    name: "Dapao.MakeImageBatch",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DapaoMakeImageBatchNode") {
            // 保存原始的 onNodeCreated
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // 添加动态输入更新函数
                this.updateInputs = function() {
                    // 检查是否已经有图像输入（避免初始化时重复添加）
                    const hasImageInput = this.inputs && this.inputs.some(input => input.name.startsWith("📸 图像"));
                    if (!hasImageInput) {
                        return;
                    }
                    
                    // 找到所有图像输入
                    const imageInputs = this.inputs.filter(input => input.name.startsWith("📸 图像"));
                    
                    // 找到最大的索引号
                    let maxIndex = 0;
                    imageInputs.forEach(input => {
                        const match = input.name.match(/📸 图像(\d+)/);
                        if (match) {
                            const index = parseInt(match[1]);
                            if (index > maxIndex) {
                                maxIndex = index;
                            }
                        }
                    });
                    
                    // 检查是否所有现有输入都已连接
                    const allConnected = imageInputs.every(input => input.link != null);
                    
                    // 如果所有输入都已连接，且未达到最大数量，添加新输入
                    if (allConnected && maxIndex < 20) {
                        const newIndex = maxIndex + 1;
                        this.addInput(`📸 图像${newIndex}`, "IMAGE");
                    }
                    
                    // 移除多余的空输入（保留至少2个）
                    const emptyInputs = imageInputs.filter(input => input.link == null);
                    if (emptyInputs.length > 1) {
                        // 找到最后一个空输入之前的所有空输入
                        const inputsToRemove = emptyInputs.slice(0, -1);
                        inputsToRemove.forEach(input => {
                            const inputIndex = this.inputs.indexOf(input);
                            if (inputIndex !== -1) {
                                this.removeInput(inputIndex);
                            }
                        });
                    }
                };
                
                // 监听连接变化
                const originalOnConnectionsChange = this.onConnectionsChange;
                this.onConnectionsChange = function(type, index, connected, link_info) {
                    if (originalOnConnectionsChange) {
                        originalOnConnectionsChange.apply(this, arguments);
                    }
                    
                    // 延迟更新，确保连接状态已更新
                    setTimeout(() => {
                        this.updateInputs();
                    }, 10);
                };
                
                return result;
            };
        }
    }
});

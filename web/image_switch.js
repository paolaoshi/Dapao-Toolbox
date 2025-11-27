import { app } from "../../scripts/app.js";

// 注册扩展
app.registerExtension({
    name: "Dapao.ImageMultiSwitch",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 只处理我们的多图片开关节点
        if (nodeData.name === "DapaoImageMultiSwitchNode") {
            
            // 保存原始的 onNodeCreated 方法
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            // 重写 onNodeCreated 方法
            nodeType.prototype.onNodeCreated = function() {
                // 调用原始方法
                const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // 添加更新输入的方法
                this.updateInputs = function() {
                    // 找到当前所有image输入的最大索引
                    let maxIndex = 0;
                    let hasEmptyInput = false;
                    let hasImageInput = false;
                    
                    // 遍历所有输入，找到最大索引和是否有空输入
                    for (let input of this.inputs) {
                        if (input.name && input.name.startsWith("image")) {
                            hasImageInput = true;
                            const index = parseInt(input.name.substring(5));
                            if (!isNaN(index)) {
                                maxIndex = Math.max(maxIndex, index);
                                if (!input.link) {
                                    hasEmptyInput = true;
                                }
                            }
                        }
                    }
                    
                    // 如果没有找到任何image输入，说明是初始状态，不需要处理
                    if (!hasImageInput) {
                        return;
                    }
                    
                    // 如果没有空输入且还没达到最大值，添加新输入
                    if (!hasEmptyInput && maxIndex < 20) {
                        const newIndex = maxIndex + 1;
                        const newInputName = `image${newIndex}`;
                        this.addInput(newInputName, "IMAGE");
                        console.log(`Added new input: ${newInputName}`);
                    }
                    
                    // 清理多余的空输入（保留最后一个空输入）
                    let emptyInputs = [];
                    for (let i = 0; i < this.inputs.length; i++) {
                        const input = this.inputs[i];
                        if (input.name && input.name.startsWith("image") && !input.link) {
                            emptyInputs.push({index: i, name: input.name});
                        }
                    }
                    
                    // 如果有多个空输入，只保留索引最大的那个
                    if (emptyInputs.length > 1) {
                        // 按索引排序
                        emptyInputs.sort((a, b) => {
                            const aNum = parseInt(a.name.substring(5));
                            const bNum = parseInt(b.name.substring(5));
                            return bNum - aNum;
                        });
                        
                        // 移除除了第一个（索引最大的）之外的所有空输入
                        for (let i = 1; i < emptyInputs.length; i++) {
                            this.removeInput(emptyInputs[i].index);
                            console.log(`Removed empty input: ${emptyInputs[i].name}`);
                        }
                    }
                };
                
                // 监听连接变化
                const onConnectionsChange = this.onConnectionsChange;
                this.onConnectionsChange = function(type, index, connected, link_info) {
                    if (onConnectionsChange) {
                        onConnectionsChange.apply(this, arguments);
                    }
                    
                    // 延迟更新，确保连接状态已更新
                    setTimeout(() => {
                        this.updateInputs();
                    }, 100);
                };
                
                return result;
            };
        }
    }
});

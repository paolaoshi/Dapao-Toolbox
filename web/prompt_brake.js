import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "Dapao.PromptBrake",
    async setup() {
        api.addEventListener("dapao.brake.start", (event) => {
            const { node_id, text, timeout } = event.detail;
            const node = app.graph.getNodeById(node_id);
            if (node) {
                node.onBrakeStart(text, timeout);
            }
        });

        api.addEventListener("dapao.brake.end", (event) => {
            const { node_id } = event.detail;
            const node = app.graph.getNodeById(node_id);
            if (node) {
                node.onBrakeEnd();
            }
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DapaoPromptBrakeNode") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                this.brakeState = {
                    active: false,
                    timeoutId: null,
                    timeLeft: 0
                };

                // 1. 获取原有的 timeout 参数 widget (由 Python 定义)
                // 尝试更宽泛的匹配，防止 emoji 编码问题
                let timeoutWidget = this.widgets && this.widgets.find(w => w.name === "timeout" || (w.name && w.name.includes("超时时间")));

                // 2. 创建大文本框
                const textWrapper = ComfyWidgets["STRING"](this, "text_content", ["STRING", { multiline: true }], app);
                this.textWidget = textWrapper.widget;
                // 关键修复：禁止序列化文本框，防止在复制节点或保存工作流时与 Timeout 参数发生值错位（导致 Timeout 变为 0）
                this.textWidget.serialize = false;
                
                if (this.textWidget && this.textWidget.inputEl) {
                    this.textWidget.inputEl.readOnly = false;
                    this.textWidget.inputEl.style.height = "250px";
                    this.textWidget.inputEl.style.fontSize = "14px";
                }

                // 3. 创建原生 DOM 按钮 (确保一定能显示)
                const btn = document.createElement("button");
                btn.textContent = "✅ 确认修改并继续 (GO!)";
                btn.style.width = "100%";
                btn.style.height = "40px";
                btn.style.marginTop = "10px";
                btn.style.marginBottom = "10px";
                btn.style.backgroundColor = "#333"; // ComfyUI 风格深灰
                btn.style.color = "#fff";
                btn.style.border = "1px solid #555";
                btn.style.borderRadius = "4px";
                btn.style.cursor = "pointer";
                btn.style.fontSize = "14px";

                // 鼠标悬停效果
                btn.onmouseenter = () => { if (!btn.disabled) btn.style.backgroundColor = "#444"; };
                btn.onmouseleave = () => { if (!btn.disabled) btn.style.backgroundColor = "#333"; };

                btn.onclick = () => {
                    this.commitBrake();
                };

                // 必须保存引用以便后续修改文字/状态
                this.domBtn = btn;
                this.addDOMWidget("btn_widget", "btn", btn, {
                    serialize: false
                });

                // 4. 创建状态显示条
                const statusWrapper = ComfyWidgets["STRING"](this, "status_info", ["STRING", { multiline: false }], app);
                this.statusWidget = statusWrapper.widget;
                this.statusWidget.label = "📜 运行状态";
                this.statusWidget.value = "💤 等待运行...";
                this.statusWidget.serialize = false;

                if (this.statusWidget && this.statusWidget.inputEl) {
                    this.statusWidget.inputEl.disabled = true;
                    this.statusWidget.inputEl.style.textAlign = "center";
                    this.statusWidget.inputEl.style.color = "#aaa";
                }

                // 5. 调整 Widget 顺序
                // 我们尝试把 Timeout 移动到 Status 下方
                if (timeoutWidget && this.widgets) {
                    const idx = this.widgets.indexOf(timeoutWidget);
                    if (idx > -1) this.widgets.splice(idx, 1);
                }

                const newWidgetsOrder = [];

                // 顺序: TextWidget(Dom) -> Button(Dom) -> Status(Canvas) -> Timeout(Canvas)

                if (this.textWidget) newWidgetsOrder.push(this.textWidget);
                // domBtn 是通过 addDOMWidget 添加的，它也会在 widgets 列表里有一个占位 widget
                // 我们找到它并放进来
                const btnWidgetObj = this.widgets && this.widgets.find(w => w.element === btn);
                if (btnWidgetObj) newWidgetsOrder.push(btnWidgetObj);

                if (this.statusWidget) newWidgetsOrder.push(this.statusWidget);
                if (timeoutWidget) newWidgetsOrder.push(timeoutWidget);

                this.widgets = newWidgetsOrder;

                // 设置节点尺寸
                this.setSize([450, 500]); // 稍微加高一点

                return r;
            };
            
            // 运行时数值守护：每帧检查参数合法性，防止因复制/加载导致的数值归零
            const onDrawForeground = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function(ctx) {
                if (onDrawForeground) onDrawForeground.apply(this, arguments);
                
                if (this.widgets) {
                    // 增强查找逻辑：不完全依赖名称，而是查找所有数字类型且有最小值的 widget
                    // 优先匹配名称包含"超时"或 name 为 "timeout" 的
                    let timeoutWidget = this.widgets.find(w => w.name === "timeout" || (w.name && w.name.includes("超时时间")));
                    
                    // 如果找不到，尝试找任何有 min 属性且 type 为 number 的 widget
                    if (!timeoutWidget) {
                        timeoutWidget = this.widgets.find(w => w.type === "number" || w.type === "INT" || (w.options && w.options.min === 5));
                    }

                    if (timeoutWidget) {
                        // 强制修正逻辑：只要值不合法（不是数字、小于5、是0、是null/undefined），统统重置
                        const val = timeoutWidget.value;
                        const isInvalid = (typeof val !== 'number') || (val < 5);
                        
                        if (isInvalid) {
                            // console.log("Fixing timeout value:", val); // 调试用
                            timeoutWidget.value = 60;
                        }
                    }
                }
            };

            // 在 onConfigure 时也执行一次强力修正
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function() {
                if (onConfigure) onConfigure.apply(this, arguments);
                
                // 此时 widgets 可能还没完全准备好，但在 configure 结束时应该有了
                // 我们延时一帧再检查，或者直接检查（如果有的话）
                if (this.widgets) {
                     let timeoutWidget = this.widgets.find(w => w.name === "timeout" || (w.name && w.name.includes("超时时间")));
                     if (!timeoutWidget) {
                        timeoutWidget = this.widgets.find(w => w.type === "number" || w.type === "INT" || (w.options && w.options.min === 5));
                     }
                     
                     if (timeoutWidget) {
                        const val = timeoutWidget.value;
                        // 这里对 configure 阶段的数据稍微宽容一点，如果是字符串形式的数字，尝试转一下
                        if (typeof val === 'string' && !isNaN(parseFloat(val))) {
                            timeoutWidget.value = parseFloat(val);
                        }
                        
                        if ((typeof timeoutWidget.value !== 'number') || (timeoutWidget.value < 5)) {
                             timeoutWidget.value = 60;
                        }
                     }
                }
            };

            nodeType.prototype.onBrakeStart = function (text, timeout) {
                this.brakeState.active = true;
                this.brakeState.timeLeft = timeout;

                if (this.textWidget) {
                    this.textWidget.value = text;
                }

                if (this.domBtn) {
                    this.domBtn.textContent = "✅ 确认修改并继续 (GO!)";
                    this.domBtn.disabled = false;
                    this.domBtn.style.backgroundColor = "#2e7d32"; // 激活时变绿
                    this.domBtn.onmouseenter = () => { if (!this.domBtn.disabled) this.domBtn.style.backgroundColor = "#388E3C"; };
                    this.domBtn.onmouseleave = () => { if (!this.domBtn.disabled) this.domBtn.style.backgroundColor = "#2e7d32"; };
                }

                if (this.statusWidget) {
                    this.statusWidget.value = `⏳ 倒计时: ${timeout} 秒`;
                }

                this.updateStatus();

                if (this.brakeState.timeoutId) clearInterval(this.brakeState.timeoutId);

                this.brakeState.timeoutId = setInterval(() => {
                    this.brakeState.timeLeft--;
                    this.updateStatus();

                    if (this.brakeState.timeLeft <= 0) {
                        clearInterval(this.brakeState.timeoutId);
                        this.brakeState.active = false;
                        this.brakeState.timeoutId = null;
                        this.statusWidget.value = "⚠️ 已超时，自动继续...";
                        if (this.domBtn) {
                            this.domBtn.textContent = "⚠️ 已超时，跳过修改";
                            this.domBtn.disabled = true;
                            this.domBtn.style.backgroundColor = "#333";
                        }
                    }
                    app.graph.setDirtyCanvas(true, true);
                }, 1000);

                app.graph.setDirtyCanvas(true, true);
            };

            nodeType.prototype.onBrakeEnd = function () {
                this.brakeState.active = false;
                if (this.brakeState.timeoutId) {
                    clearInterval(this.brakeState.timeoutId);
                    this.brakeState.timeoutId = null;
                }
                this.statusWidget.value = "✨ 运行完成";
                if (this.domBtn) {
                    this.domBtn.textContent = "✨ 运行完成";
                    this.domBtn.disabled = true;
                    this.domBtn.style.backgroundColor = "#333";
                }
                app.graph.setDirtyCanvas(true, true);
            };

            nodeType.prototype.updateStatus = function () {
                if (this.brakeState.active && this.statusWidget) {
                    this.statusWidget.value = `⏳ 倒计时: ${this.brakeState.timeLeft} 秒 | 正在等待...`;
                }
            };

            nodeType.prototype.commitBrake = function () {
                if (!this.brakeState.active) return;

                const newText = this.textWidget.value;

                if (this.brakeState.timeoutId) {
                    clearInterval(this.brakeState.timeoutId);
                    this.brakeState.timeoutId = null;
                }

                this.statusWidget.value = "🚀 提交中...";
                if (this.domBtn) {
                    this.domBtn.textContent = "🚀 提交中...";
                    this.domBtn.disabled = true;
                }

                api.fetchApi("/dapao/brake/update", {
                    method: "POST",
                    body: JSON.stringify({
                        node_id: this.id.toString(),
                        text: newText,
                        action: "continue"
                    }),
                }).then(response => {
                    if (response.ok) {
                        this.statusWidget.value = "✅ 已提交，继续执行...";
                        if (this.domBtn) {
                            this.domBtn.textContent = "✅ 已提交";
                            this.domBtn.style.backgroundColor = "#1565c0"; // 蓝色
                            this.domBtn.onmouseenter = null;
                            this.domBtn.onmouseleave = null;
                        }
                    } else {
                        this.statusWidget.value = "❌ 提交失败";
                        if (this.domBtn) {
                            this.domBtn.textContent = "❌ 重试";
                            this.domBtn.disabled = false;
                            this.domBtn.style.backgroundColor = "#c62828"; // 红色
                        }
                        alert("提交失败，请检查控制台");
                    }
                    app.graph.setDirtyCanvas(true, true);
                }).catch(err => {
                    console.error(err);
                    this.statusWidget.value = "❌ 网络错误";
                });
            };
        }
    },
});

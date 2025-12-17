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
                let timeoutWidget = this.widgets.find(w => w.name === "timeout" || w.name.includes("超时时间"));

                // 2. 创建大文本框
                const textWrapper = ComfyWidgets["STRING"](this, "text_content", ["STRING", { multiline: true }], app);
                this.textWidget = textWrapper.widget;
                this.textWidget.inputEl.readOnly = false;
                this.textWidget.inputEl.style.height = "250px";
                this.textWidget.inputEl.style.fontSize = "14px";

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
                this.statusWidget = this.addWidget("text", "📜 运行状态", "💤 等待运行...", () => { }, { serialize: false });
                this.statusWidget.inputEl.disabled = true;
                this.statusWidget.inputEl.style.textAlign = "center";
                this.statusWidget.inputEl.style.color = "#aaa";

                // 5. 调整 Widget 顺序
                // 我们尝试把 Timeout 移动到 Status 下方
                if (timeoutWidget) {
                    const idx = this.widgets.indexOf(timeoutWidget);
                    if (idx > -1) this.widgets.splice(idx, 1);
                }

                const newWidgetsOrder = [];

                // 顺序: TextWidget(Dom) -> Button(Dom) -> Status(Canvas) -> Timeout(Canvas)

                if (this.textWidget) newWidgetsOrder.push(this.textWidget);
                // domBtn 是通过 addDOMWidget 添加的，它也会在 widgets 列表里有一个占位 widget
                // 我们找到它并放进来
                const btnWidgetObj = this.widgets.find(w => w.element === btn);
                if (btnWidgetObj) newWidgetsOrder.push(btnWidgetObj);

                if (this.statusWidget) newWidgetsOrder.push(this.statusWidget);
                if (timeoutWidget) newWidgetsOrder.push(timeoutWidget);

                this.widgets = newWidgetsOrder;

                // 设置节点尺寸
                this.setSize([450, 500]); // 稍微加高一点

                return r;
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
                    btn.onmouseenter = () => { if (!btn.disabled) btn.style.backgroundColor = "#388E3C"; };
                    btn.onmouseleave = () => { if (!btn.disabled) btn.style.backgroundColor = "#2e7d32"; };
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

/**
 * 图像分色框选节点 - 使用 addDOMWidget 方式实现画板
 * 支持矩形框、椭圆框、填充块、画笔、橡皮擦、直线、箭头等工具
 *
 * Time: 2026/02/27
 * Author: Dapao
 */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_TYPE = "DapaoImageColorBoxNode";
const NODE_MIN_WIDTH = 520;

const PRESET_COLORS = [
    "#FF3B30", "#FF9500", "#FFCC00", "#34C759",
    "#007AFF", "#5856D6", "#FF2D55", "#00C7BE",
    "#FFFFFF", "#C0C0C0", "#808080", "#000000",
];

const TOOLS = [
    { key: "rect",         label: "□矩形框" },
    { key: "ellipse",      label: "○椭圆框" },
    { key: "fill_rect",    label: "■矩形块" },
    { key: "fill_ellipse", label: "●椭圆块" },
    { key: "line",         label: "╱直线" },
    { key: "arrow",        label: "→箭头" },
    { key: "brush",        label: "✎画笔" },
    { key: "eraser",       label: "✕橡皮擦" },
];

function hexToRgba(hex, opacity) {
    hex = hex.replace("#", "");
    if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${opacity})`;
}

function createPainterDOM(node) {
    const state = {
        toolKey: "rect", color: "#FF3B30", opacity: 1.0,
        lineWidth: 3, brushSize: 8, annotations: [], history: [],
        isDrawing: false, startRX: 0, startRY: 0,
        currentAnn: null, brushPoints: [], img: null,
    };

    const wrapper = document.createElement("div");
    wrapper.style.cssText = "width:100%;background:#1e1e1e;padding:6px;box-sizing:border-box;user-select:none;";

    // ── 工具栏（两行4列） ──
    const toolbar = document.createElement("div");
    toolbar.style.cssText = "display:grid;grid-template-columns:repeat(4,1fr);gap:3px;margin-bottom:6px;";
    const toolBtns = [];
    TOOLS.forEach((t) => {
        const btn = document.createElement("button");
        btn.textContent = t.label;
        btn.style.cssText = "padding:4px 2px;border:none;border-radius:4px;cursor:pointer;font-size:11px;font-weight:bold;color:#fff;background:" + (t.key === "rect" ? "#0a84ff" : "#3a3a3a") + ";";
        btn.addEventListener("click", () => {
            state.toolKey = t.key;
            toolBtns.forEach((b, j) => b.style.background = TOOLS[j].key === t.key ? "#0a84ff" : "#3a3a3a");
        });
        toolBtns.push(btn);
        toolbar.appendChild(btn);
    });
    wrapper.appendChild(toolbar);

    // ── 颜色选择 ──
    const colorRow = document.createElement("div");
    colorRow.style.cssText = "display:flex;gap:3px;margin-bottom:6px;flex-wrap:wrap;";
    const colorBtns = [];
    PRESET_COLORS.forEach((c) => {
        const sw = document.createElement("div");
        sw.style.cssText = `width:18px;height:18px;border-radius:3px;cursor:pointer;background:${c};border:2px solid ${c === state.color ? "#fff" : "transparent"};box-sizing:border-box;`;
        sw.addEventListener("click", () => {
            state.color = c;
            colorBtns.forEach(s => s.style.borderColor = "transparent");
            sw.style.borderColor = "#fff";
        });
        colorBtns.push(sw);
        colorRow.appendChild(sw);
    });
    wrapper.appendChild(colorRow);

    // ── 滑块行 ──
    const sliderRow = document.createElement("div");
    sliderRow.style.cssText = "display:flex;gap:8px;margin-bottom:6px;align-items:center;font-size:11px;color:#aaa;";

    const opLabel = document.createElement("span");
    opLabel.textContent = "透明度:";
    const opSlider = document.createElement("input");
    Object.assign(opSlider, { type: "range", min: "5", max: "100", value: "100" });
    opSlider.style.cssText = "flex:1;height:14px;accent-color:#0a84ff;";
    const opVal = document.createElement("span");
    opVal.textContent = "100%";
    opSlider.addEventListener("input", () => {
        state.opacity = parseInt(opSlider.value) / 100;
        opVal.textContent = opSlider.value + "%";
    });

    const lwLabel = document.createElement("span");
    lwLabel.textContent = "线宽:";
    const lwSlider = document.createElement("input");
    Object.assign(lwSlider, { type: "range", min: "1", max: "30", value: "3" });
    lwSlider.style.cssText = "flex:1;height:14px;accent-color:#0a84ff;";
    const lwVal = document.createElement("span");
    lwVal.textContent = "3px";
    lwSlider.addEventListener("input", () => {
        state.lineWidth = parseInt(lwSlider.value);
        lwVal.textContent = lwSlider.value + "px";
    });

    sliderRow.append(opLabel, opSlider, opVal, lwLabel, lwSlider, lwVal);
    wrapper.appendChild(sliderRow);

    // ── 画笔大小滑块行 ──
    const brushRow = document.createElement("div");
    brushRow.style.cssText = "display:flex;gap:8px;margin-bottom:6px;align-items:center;font-size:11px;color:#aaa;";
    const bsLabel = document.createElement("span");
    bsLabel.textContent = "画笔/橡皮擦:";
    const bsSlider = document.createElement("input");
    Object.assign(bsSlider, { type: "range", min: "2", max: "50", value: "8" });
    bsSlider.style.cssText = "flex:1;height:14px;accent-color:#ff9500;";
    const bsVal = document.createElement("span");
    bsVal.textContent = "8px";
    bsSlider.addEventListener("input", () => {
        state.brushSize = parseInt(bsSlider.value);
        bsVal.textContent = bsSlider.value + "px";
    });
    brushRow.append(bsLabel, bsSlider, bsVal);
    wrapper.appendChild(brushRow);

    // ── 上传按钮 ──
    const uploadBtn = document.createElement("button");
    uploadBtn.textContent = "选择文件上传";
    uploadBtn.style.cssText = "width:100%;padding:5px;border:1px solid #555;border-radius:4px;background:#2a2a2a;color:#ccc;cursor:pointer;font-size:12px;margin-bottom:6px;";
    wrapper.appendChild(uploadBtn);

    // ── Canvas 画板 ──
    const canvasWrap = document.createElement("div");
    canvasWrap.style.cssText = "position:relative;width:100%;background:#111;overflow:hidden;";
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 200;
    canvas.style.cssText = "display:block;width:100%;height:auto;cursor:crosshair;";
    canvasWrap.appendChild(canvas);
    wrapper.appendChild(canvasWrap);

    // ── 信息栏 ──
    const infoBar = document.createElement("div");
    infoBar.style.cssText = "text-align:center;font-size:10px;color:#888;padding:4px 0;";
    infoBar.textContent = "请在上方选择图像文件";
    wrapper.appendChild(infoBar);

    // ── 按钮行 ──
    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:6px;margin-top:6px;";
    const undoBtn = document.createElement("button");
    undoBtn.textContent = "↩ 撤销";
    undoBtn.style.cssText = "flex:1;padding:5px;border:1px solid #444;border-radius:4px;background:#2a2a2a;color:#ccc;cursor:pointer;font-size:12px;";
    const clearBtn = document.createElement("button");
    clearBtn.textContent = "🗑 清空标注";
    clearBtn.style.cssText = "flex:1;padding:5px;border:1px solid #444;border-radius:4px;background:#2a2a2a;color:#ccc;cursor:pointer;font-size:12px;";
    btnRow.append(undoBtn, clearBtn);
    wrapper.appendChild(btnRow);

    return { wrapper, canvas, canvasWrap, infoBar, state, undoBtn, clearBtn, uploadBtn };
}

function redrawCanvas(canvas, state, infoBar) {
    const ctx = canvas.getContext("2d");
    const cw = canvas.width, ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    if (!state.img) {
        ctx.fillStyle = "#333";
        ctx.font = "14px Arial";
        ctx.textAlign = "center";
        ctx.fillText("请在上方选择图像文件", cw / 2, ch / 2);
        return;
    }

    // 先画原图
    ctx.drawImage(state.img, 0, 0, cw, ch);

    // 在离屏 Canvas 上绘制标注层（橡皮擦只擦标注层）
    if (!state._offscreen || state._offscreen.width !== cw || state._offscreen.height !== ch) {
        state._offscreen = document.createElement("canvas");
        state._offscreen.width = cw;
        state._offscreen.height = ch;
    }
    const offCtx = state._offscreen.getContext("2d");
    offCtx.clearRect(0, 0, cw, ch);

    const allAnns = [...state.annotations];
    if (state.currentAnn) allAnns.push(state.currentAnn);

    for (const a of allAnns) {
        drawAnnotation(offCtx, cw, ch, a);
    }

    // 将标注层合成到主画布
    ctx.drawImage(state._offscreen, 0, 0);

    infoBar.textContent = state.img.naturalWidth + " × " + state.img.naturalHeight +
        "  |  " + state.annotations.length + " 个标注";
}

function drawAnnotation(ctx, cw, ch, a) {
    ctx.save();
    const op = a.opacity;
    const lw = a.line_width || a.brushSize || 3;
    ctx.lineWidth = lw;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (a.shape === "brush" && a.points && a.points.length > 1) {
        ctx.strokeStyle = hexToRgba(a.color, op);
        ctx.lineWidth = a.brushSize || 8;
        ctx.beginPath();
        ctx.moveTo(a.points[0][0] * cw, a.points[0][1] * ch);
        for (let i = 1; i < a.points.length; i++) {
            ctx.lineTo(a.points[i][0] * cw, a.points[i][1] * ch);
        }
        ctx.stroke();
    } else if (a.shape === "eraser" && a.points && a.points.length > 1) {
        ctx.globalCompositeOperation = "destination-out";
        ctx.strokeStyle = "rgba(0,0,0,1)";
        ctx.lineWidth = a.brushSize || 15;
        ctx.beginPath();
        ctx.moveTo(a.points[0][0] * cw, a.points[0][1] * ch);
        for (let i = 1; i < a.points.length; i++) {
            ctx.lineTo(a.points[i][0] * cw, a.points[i][1] * ch);
        }
        ctx.stroke();
    } else {
        const x1 = a.x1 * cw, y1 = a.y1 * ch;
        const x2 = a.x2 * cw, y2 = a.y2 * ch;
        const w = x2 - x1, h = y2 - y1;
        ctx.strokeStyle = hexToRgba(a.color, op);
        ctx.fillStyle = hexToRgba(a.color, op);

        if (a.shape === "rect") {
            ctx.strokeRect(x1, y1, w, h);
        } else if (a.shape === "ellipse") {
            drawEllipse(ctx, x1, y1, x2, y2, false);
        } else if (a.shape === "fill_rect") {
            ctx.fillRect(x1, y1, w, h);
        } else if (a.shape === "fill_ellipse") {
            drawEllipse(ctx, x1, y1, x2, y2, true);
        } else if (a.shape === "line") {
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        } else if (a.shape === "arrow") {
            drawArrow(ctx, x1, y1, x2, y2, lw);
        }
    }
    ctx.restore();
}

function drawEllipse(ctx, x1, y1, x2, y2, fill) {
    const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
    const rx = Math.abs(x2 - x1) / 2, ry = Math.abs(y2 - y1) / 2;
    if (rx < 1 || ry < 1) return;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    if (fill) ctx.fill();
    else ctx.stroke();
}

function drawArrow(ctx, x1, y1, x2, y2, lw) {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const headLen = Math.max(lw * 4, 12);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - headLen * Math.cos(angle - 0.4), y2 - headLen * Math.sin(angle - 0.4));
    ctx.lineTo(x2 - headLen * Math.cos(angle + 0.4), y2 - headLen * Math.sin(angle + 0.4));
    ctx.closePath();
    ctx.fill();
}

function bindCanvasEvents(canvas, state, infoBar, syncJson) {
    function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        return {
            rx: (e.clientX - rect.left) / rect.width,
            ry: (e.clientY - rect.top) / rect.height,
        };
    }

    canvas.addEventListener("pointerdown", (e) => {
        if (!state.img) return;
        const { rx, ry } = getPos(e);
        if (rx < 0 || rx > 1 || ry < 0 || ry > 1) return;
        state.isDrawing = true;
        state.startRX = rx;
        state.startRY = ry;
        canvas.setPointerCapture(e.pointerId);

        if (state.toolKey === "brush" || state.toolKey === "eraser") {
            state.brushPoints = [[rx, ry]];
        }
    });

    canvas.addEventListener("pointermove", (e) => {
        if (!state.isDrawing) return;
        const { rx, ry } = getPos(e);
        const cx = Math.max(0, Math.min(1, rx));
        const cy = Math.max(0, Math.min(1, ry));

        if (state.toolKey === "brush" || state.toolKey === "eraser") {
            state.brushPoints.push([cx, cy]);
            state.currentAnn = {
                shape: state.toolKey,
                points: [...state.brushPoints],
                color: state.color,
                opacity: state.opacity,
                brushSize: state.brushSize,
            };
        } else {
            state.currentAnn = {
                shape: state.toolKey,
                x1: Math.min(state.startRX, cx),
                y1: Math.min(state.startRY, cy),
                x2: Math.max(state.startRX, cx),
                y2: Math.max(state.startRY, cy),
                color: state.color,
                opacity: state.opacity,
                line_width: state.lineWidth,
            };
        }
        redrawCanvas(canvas, state, infoBar);
    });

    canvas.addEventListener("pointerup", (e) => {
        if (!state.isDrawing) return;
        state.isDrawing = false;
        const a = state.currentAnn;
        if (a) {
            let valid = false;
            if (a.shape === "brush" || a.shape === "eraser") {
                valid = a.points && a.points.length > 2;
            } else {
                valid = (a.x2 - a.x1) > 0.003 && (a.y2 - a.y1) > 0.003;
            }
            if (valid) {
                state.history.push(JSON.parse(JSON.stringify(state.annotations)));
                if (state.history.length > 50) state.history.shift();
                state.annotations.push({ ...a });
                syncJson();
            }
        }
        state.currentAnn = null;
        state.brushPoints = [];
        redrawCanvas(canvas, state, infoBar);
    });
}

function loadImageToCanvas(filename, canvas, state, infoBar) {
    if (!filename) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
        state.img = img;
        const containerW = canvas.parentElement.clientWidth || 500;
        const asp = img.naturalHeight / img.naturalWidth;
        const maxH = 800;
        let dW = containerW, dH = Math.round(containerW * asp);
        if (dH > maxH) { dH = maxH; dW = Math.round(maxH / asp); }
        canvas.width = dW;
        canvas.height = dH;
        canvas.style.width = "100%";
        canvas.style.height = "auto";
        redrawCanvas(canvas, state, infoBar);
    };
    img.onerror = () => console.warn("[DapaoColorBox] 图像加载失败:", filename);
    img.src = api.apiURL(
        "/view?filename=" + encodeURIComponent(filename) + "&type=input&t=" + Date.now()
    );
}

// ─── 注册扩展 ───────────────────────────────────────────────────────────────
app.registerExtension({
    name: "Dapao.ImageColorBox",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_TYPE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
            const node = this;

            // 设置节点最小宽度
            if (node.size[0] < NODE_MIN_WIDTH) {
                node.size[0] = NODE_MIN_WIDTH;
            }

            const dom = createPainterDOM(node);
            const { wrapper, canvas, canvasWrap, infoBar, state, undoBtn, clearBtn, uploadBtn } = dom;

            function syncJson() {
                const jsonStr = JSON.stringify(state.annotations);
                const jw = node.widgets?.find(w => w.name === "annotations_json");
                if (jw) jw.value = jsonStr;
            }

            bindCanvasEvents(canvas, state, infoBar, syncJson);

            undoBtn.addEventListener("click", () => {
                if (!state.history.length) return;
                state.annotations = state.history.pop();
                syncJson();
                redrawCanvas(canvas, state, infoBar);
            });

            clearBtn.addEventListener("click", () => {
                state.history.push(JSON.parse(JSON.stringify(state.annotations)));
                state.annotations = [];
                syncJson();
                redrawCanvas(canvas, state, infoBar);
            });

            // 上传按钮
            const fileInput = document.createElement("input");
            fileInput.type = "file";
            fileInput.accept = "image/png,image/jpeg,image/webp,image/bmp";
            fileInput.style.display = "none";
            wrapper.appendChild(fileInput);
            uploadBtn.addEventListener("click", () => fileInput.click());

            fileInput.addEventListener("change", async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const formData = new FormData();
                formData.append("image", file, file.name);
                formData.append("overwrite", "true");
                try {
                    const resp = await api.fetchApi("/upload/image", {
                        method: "POST",
                        body: formData,
                    });
                    const data = await resp.json();
                    if (data?.name) {
                        const imgW = node.widgets?.find(w => w.name === "image");
                        if (imgW) {
                            if (imgW.options?.values && !imgW.options.values.includes(data.name)) {
                                imgW.options.values.push(data.name);
                            }
                            imgW.value = data.name;
                            if (imgW.callback) imgW.callback(data.name);
                        }
                        loadImageToCanvas(data.name, canvas, state, infoBar);
                    }
                } catch (err) {
                    console.error("[DapaoColorBox] 上传失败:", err);
                }
                fileInput.value = "";
            });

            // 隐藏 annotations_json widget
            setTimeout(() => {
                for (const w of node.widgets) {
                    if (w.name === "annotations_json") {
                        w.type = "converted-widget";
                        w.computeSize = () => [0, -4];
                    }
                }
            }, 50);

            // 用 addDOMWidget 添加画板
            node.addDOMWidget("color_box_painter", "custom", wrapper, {
                setValue(v) {},
                getValue() { return JSON.stringify(state.annotations); },
            });

            node._cbState = state;
            node._cbCanvas = canvas;
            node._cbInfoBar = infoBar;
            node._cbSyncJson = syncJson;

            // 监听图像选择变化
            setTimeout(() => {
                const imgW = node.widgets?.find(w => w.name === "image");
                if (imgW) {
                    const origCb = imgW.callback;
                    imgW.callback = function (v) {
                        if (origCb) origCb.call(this, v);
                        loadImageToCanvas(v, canvas, state, infoBar);
                    };
                    if (imgW.value) {
                        loadImageToCanvas(imgW.value, canvas, state, infoBar);
                    }
                }
                node.setSize([Math.max(node.size[0], NODE_MIN_WIDTH), node.computeSize()[1]]);
            }, 100);

            return r;
        };
    },
});

console.warn("[Dapao-Toolbox] Skip loading backup extension file realtime_image_adjust_original.js");


                const img = new Image();

                img.onload = () => {
                    console.log(`[实时图像调整] 节点 ${this.id} 图像加载完成: ${img.width}x${img.height}`);

                    // 创建临时画布获取像素数据
                    const tempCanvas = document.createElement('canvas');
                    tempCanvas.width = img.width;
                    tempCanvas.height = img.height;
                    const tempCtx = tempCanvas.getContext('2d');

                    // 绘制图像
                    tempCtx.drawImage(img, 0, 0);

                    // 获取像素数据
                    const imageData = tempCtx.getImageData(0, 0, img.width, img.height);

                    // 转换为二维数组
                    const pixelArray = [];
                    for (let y = 0; y < img.height; y++) {
                        const row = [];
                        for (let x = 0; x < img.width; x++) {
                            const idx = (y * img.width + x) * 4;
                            row.push([
                                imageData.data[idx],
                                imageData.data[idx + 1],
                                imageData.data[idx + 2]
                            ]);
                        }
                        pixelArray.push(row);
                    }

                    // 保存原始图像数据
                    this.originalImageData = pixelArray;
                    this.originalImageRendered = false;

                    // 重置应用状态（新的工作流执行）
                    this.hasApplied = false;
                    this.isApplying = false;

                    // 重置调整标记和定时器
                    this.hasAdjusted = false;
                    this.clearAdjustmentTimers();

                    // 更新预览（不发送到后端）
                    this.updatePreview(true);
                };

                img.onerror = () => {
                    console.error(`[实时图像调整] 节点 ${this.id} 图像加载失败`);
                };

                img.src = base64Data;
            };

            // 添加节点时创建预览区域
            const onAdded = nodeType.prototype.onAdded;
            nodeType.prototype.onAdded = function () {
                const result = onAdded?.apply(this, arguments);

                if (!this.previewElement && this.id !== undefined && this.id !== -1) {
                    console.log(`[实时图像调整] 节点 ${this.id} 创建预览区域`);

                    const previewContainer = document.createElement("div");
                    previewContainer.style.position = "relative";
                    previewContainer.style.width = "100%";
                    previewContainer.style.height = "100%";
                    previewContainer.style.backgroundColor = "#1a1a1a";
                    previewContainer.style.borderRadius = "8px";
                    previewContainer.style.overflow = "hidden";
                    previewContainer.style.border = "2px solid rgba(100, 189, 200, 0.5)";

                    const canvas = document.createElement("canvas");
                    canvas.style.width = "100%";
                    canvas.style.height = "100%";
                    canvas.style.objectFit = "contain";

                    previewContainer.appendChild(canvas);

                    this.canvas = canvas;
                    this.previewElement = previewContainer;
                    this.widgets ||= [];
                    this.widgets_up = true;

                    requestAnimationFrame(() => {
                        if (this.widgets) {
                            this.previewWidget = this.addDOMWidget("preview", "preview", previewContainer, {
                                serialize: false,
                                hideOnZoom: false
                            });
                            this.setDirtyCanvas(true, true);
                        }
                    });
                }

                return result;
            };

            // 计算裁剪起始坐标
            nodeType.prototype.calculateCropPosition = function (originalWidth, originalHeight, targetWidth, targetHeight, position) {
                let cropX = 0;
                let cropY = 0;

                switch (position) {
                    case "center":
                        cropX = Math.floor((originalWidth - targetWidth) / 2);
                        cropY = Math.floor((originalHeight - targetHeight) / 2);
                        break;
                    case "top":
                        cropX = Math.floor((originalWidth - targetWidth) / 2);
                        cropY = 0;
                        break;
                    case "bottom":
                        cropX = Math.floor((originalWidth - targetWidth) / 2);
                        cropY = originalHeight - targetHeight;
                        break;
                    case "left":
                        cropX = 0;
                        cropY = Math.floor((originalHeight - targetHeight) / 2);
                        break;
                    case "right":
                        cropX = originalWidth - targetWidth;
                        cropY = Math.floor((originalHeight - targetHeight) / 2);
                        break;
                    case "top-left":
                        cropX = 0;
                        cropY = 0;
                        break;
                    case "top-right":
                        cropX = originalWidth - targetWidth;
                        cropY = 0;
                        break;
                    case "bottom-left":
                        cropX = 0;
                        cropY = originalHeight - targetHeight;
                        break;
                    case "bottom-right":
                        cropX = originalWidth - targetWidth;
                        cropY = originalHeight - targetHeight;
                        break;
                    default:
                        cropX = Math.floor((originalWidth - targetWidth) / 2);
                        cropY = Math.floor((originalHeight - targetHeight) / 2);
                }

                // 确保坐标不会是负数
                cropX = Math.max(0, cropX);
                cropY = Math.max(0, cropY);

                // 确保不会超出边界
                cropX = Math.min(cropX, Math.max(0, originalWidth - targetWidth));
                cropY = Math.min(cropY, Math.max(0, originalHeight - targetHeight));

                return { cropX, cropY };
            };

            // 更新预览（智能裁剪+缩放）
            nodeType.prototype.updatePreview = function (onlyPreview = true) {
                if (!this.originalImageData || !this.canvas) {
                    return;
                }

                if (this.updateTimeout) {
                    clearTimeout(this.updateTimeout);
                }

                this.updateTimeout = setTimeout(() => {
                    requestAnimationFrame(() => {
                        const ctx = this.canvas.getContext("2d");
                        const originalWidth = this.originalImageData[0].length;
                        const originalHeight = this.originalImageData.length;

                        console.log(`[实时图像调整] 开始处理: 原始尺寸=${originalWidth}x${originalHeight}`);

                        // 1. 创建原始图像画布
                        if (!this.tempCanvas || !this.originalImageRendered) {
                            this.tempCanvas = document.createElement('canvas');
                            this.tempCanvas.width = originalWidth;
                            this.tempCanvas.height = originalHeight;
                            const tempCtx = this.tempCanvas.getContext('2d');

                            const imgData = new ImageData(originalWidth, originalHeight);
                            for (let y = 0; y < originalHeight; y++) {
                                for (let x = 0; x < originalWidth; x++) {
                                    const idx = (y * originalWidth + x) * 4;
                                    imgData.data[idx] = this.originalImageData[y][x][0];
                                    imgData.data[idx + 1] = this.originalImageData[y][x][1];
                                    imgData.data[idx + 2] = this.originalImageData[y][x][2];
                                    imgData.data[idx + 3] = 255;
                                }
                            }
                            tempCtx.putImageData(imgData, 0, 0);
                            this.originalImageRendered = true;
                        }

                        // 2. 计算目标尺寸
                        let targetWidth = this.target_width || 0;
                        let targetHeight = this.target_height || 0;

                        if (targetWidth === 0 && targetHeight === 0) {
                            // 保持原始尺寸
                            targetWidth = originalWidth;
                            targetHeight = originalHeight;
                        } else if (targetWidth === 0 && targetHeight > 0) {
                            // 只设置了高度，按比例计算宽度
                            if (this.keep_aspect) {
                                targetWidth = Math.round(targetHeight * originalWidth / originalHeight);
                            } else {
                                targetWidth = originalWidth;
                            }
                        } else if (targetWidth > 0 && targetHeight === 0) {
                            // 只设置了宽度，按比例计算高度
                            if (this.keep_aspect) {
                                targetHeight = Math.round(targetWidth * originalHeight / originalWidth);
                            } else {
                                targetHeight = originalHeight;
                            }
                        }
                        // 如果两者都设置了，就直接使用

                        console.log(`[实时图像调整] 目标尺寸: ${targetWidth}x${targetHeight} (锁定比例=${this.keep_aspect})`);

                        // 3. 应用色彩调整到整个图像
                        const adjustedCanvas = document.createElement('canvas');
                        adjustedCanvas.width = originalWidth;
                        adjustedCanvas.height = originalHeight;
                        const adjustedCtx = adjustedCanvas.getContext('2d');
                        adjustedCtx.drawImage(this.tempCanvas, 0, 0);

                        const imageData = adjustedCtx.getImageData(0, 0, originalWidth, originalHeight);
                        const adjustedData = this.adjustColors(imageData);
                        adjustedCtx.putImageData(adjustedData, 0, 0);

                        // 4. 智能裁剪+缩放
                        const originalAspect = originalWidth / originalHeight;
                        const targetAspect = targetWidth / targetHeight;

                        let intermediateCanvas = adjustedCanvas;
                        let intermediateWidth = originalWidth;
                        let intermediateHeight = originalHeight;

                        // 如果目标比例与原始比例不同，需要先裁剪
                        if (Math.abs(originalAspect - targetAspect) > 0.01) {
                            console.log(`[实时图像调整] 比例不一致，需要裁剪: 原始=${originalAspect.toFixed(2)}, 目标=${targetAspect.toFixed(2)}`);

                            // 计算需要裁剪到的尺寸（保持目标比例）
                            let cropWidth, cropHeight;
                            if (targetAspect > originalAspect) {
                                // 目标更宽，需要裁剪高度
                                cropWidth = originalWidth;
                                cropHeight = Math.round(originalWidth / targetAspect);
                            } else {
                                // 目标更高，需要裁剪宽度
                                cropHeight = originalHeight;
                                cropWidth = Math.round(originalHeight * targetAspect);
                            }

                            // 计算裁剪起始位置
                            const position = this.crop_position || "center";
                            const { cropX, cropY } = this.calculateCropPosition(originalWidth, originalHeight, cropWidth, cropHeight, position);

                            console.log(`[实时图像调整] 裁剪: ${cropWidth}x${cropHeight}, 位置: ${position}, 起始: (${cropX}, ${cropY})`);

                            // 创建裁剪后的画布
                            intermediateCanvas = document.createElement('canvas');
                            intermediateCanvas.width = cropWidth;
                            intermediateCanvas.height = cropHeight;
                            const intermediateCtx = intermediateCanvas.getContext('2d');
                            intermediateCtx.drawImage(adjustedCanvas, cropX, cropY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight);

                            intermediateWidth = cropWidth;
                            intermediateHeight = cropHeight;
                        }

                        // 5. 缩放到目标尺寸
                        this.canvas.width = targetWidth;
                        this.canvas.height = targetHeight;
                        ctx.clearRect(0, 0, targetWidth, targetHeight);
                        ctx.drawImage(intermediateCanvas, 0, 0, intermediateWidth, intermediateHeight, 0, 0, targetWidth, targetHeight);

                        // 保存最终数据（等待用户点击应用按钮）
                        this.finalImageData = ctx.getImageData(0, 0, targetWidth, targetHeight);

                        console.log(`[实时图像调整] 预览更新完成！`);
                    });
                }, this.isAdjusting ? 50 : 0);
            };

            // 应用色彩调整
            nodeType.prototype.adjustColors = function (imageData) {
                const brightness = this["亮度"] || 1.0;
                const contrast = this["对比度"] || 1.0;
                const saturation = this["饱和度"] || 1.0;

                const result = new Uint8ClampedArray(imageData.data);
                const len = result.length;

                const contrastFactor = contrast;
                const contrastOffset = 128 * (1 - contrast);

                for (let i = 0; i < len; i += 4) {
                    let r = Math.min(255, result[i] * brightness);
                    let g = Math.min(255, result[i + 1] * brightness);
                    let b = Math.min(255, result[i + 2] * brightness);

                    r = r * contrastFactor + contrastOffset;
                    g = g * contrastFactor + contrastOffset;
                    b = b * contrastFactor + contrastOffset;

                    if (saturation !== 1.0) {
                        const avg = r * 0.299 + g * 0.587 + b * 0.114;
                        r = avg + (r - avg) * saturation;
                        g = avg + (g - avg) * saturation;
                        b = avg + (b - avg) * saturation;
                    }

                    result[i] = Math.min(255, Math.max(0, r));
                    result[i + 1] = Math.min(255, Math.max(0, g));
                    result[i + 2] = Math.min(255, Math.max(0, b));
                }

                return new ImageData(result, imageData.width, imageData.height);
            };

            // 应用调整（用户点击按钮时调用）
            nodeType.prototype.applyAdjustments = async function () {
                // 清除所有定时器
                this.clearAdjustmentTimers();

                // 检查是否已经应用过
                if (this.hasApplied) {
                    console.log("[实时图像调整] 本次工作流已应用过，无需重复应用");
                    alert("⚠️ 本次工作流已应用过调整！\n\n如需再次调整请重新执行工作流。");
                    return;
                }

                if (!this.finalImageData) {
                    console.error("[实时图像调整] 没有可用的图像数据");
                    return;
                }

                // 防止重复点击
                if (this.isApplying) {
                    console.log("[实时图像调整] 正在应用中，请勿重复点击");
                    return;
                }

                this.isApplying = true;

                try {
                    const endpoint = '/dapao_toolbox/realtime_image_adjust/apply';
                    const nodeId = String(this.id);

                    console.log(`[实时图像调整] 节点 ${nodeId} 开始应用调整: ${this.finalImageData.width}x${this.finalImageData.height}`);

                    const response = await api.fetchApi(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            node_id: nodeId,
                            adjusted_data: Array.from(this.finalImageData.data),
                            width: this.finalImageData.width,
                            height: this.finalImageData.height
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`服务器返回错误: ${response.status}`);
                    }

                    const result = await response.json();

                    if (result.success) {
                        console.log(`[实时图像调整] 节点 ${nodeId} 应用成功！工作流将继续执行`);

                        // 标记已应用，防止再次应用
                        this.hasApplied = true;

                        // 清除最终图像数据，防止意外再次发送
                        this.finalImageData = null;
                    } else {
                        console.warn(`[实时图像调整] 节点 ${nodeId} 应用失败:`, result.error);
                    }

                } catch (error) {
                    console.error(`[实时图像调整] 节点 ${this.id} 应用失败:`, error);
                } finally {
                    this.isApplying = false;
                }
            };

            // 标记用户已调整参数，启动定时器
            nodeType.prototype.markAsAdjusted = function () {
                if (this.hasApplied) {
                    // 如果已经应用过，不启动定时器
                    return;
                }

                this.hasAdjusted = true;

                // 清除旧定时器
                this.clearAdjustmentTimers();

                // 启动20秒警告定时器
                this.warningTimer = setTimeout(() => {
                    if (!this.hasApplied && this.hasAdjusted) {
                        console.log("[实时图像调整] 20秒无操作，提示用户");
                        alert("⏰ 提示：您已调整参数超过20秒\n\n请点击【✅ 应用调整并继续】按钮以继续工作流。\n\n如果40秒内仍未操作，将自动应用当前调整。");
                    }
                }, 20000);  // 20秒

                // 启动40秒自动应用定时器
                this.autoApplyTimer = setTimeout(() => {
                    if (!this.hasApplied && this.hasAdjusted) {
                        console.log("[实时图像调整] 40秒无操作，自动应用调整");
                        alert("⏰ 自动应用：超过40秒未操作\n\n系统将自动应用当前调整并继续工作流。");
                        // 延迟1秒后自动应用，让用户看到提示
                        setTimeout(() => {
                            this.applyAdjustments();
                        }, 1000);
                    }
                }, 40000);  // 40秒

                console.log("[实时图像调整] 已启动智能等待定时器 (20秒提示, 40秒自动应用)");
            };

            // 清除所有调整定时器
            nodeType.prototype.clearAdjustmentTimers = function () {
                if (this.warningTimer) {
                    clearTimeout(this.warningTimer);
                    this.warningTimer = null;
                }
                if (this.autoApplyTimer) {
                    clearTimeout(this.autoApplyTimer);
                    this.autoApplyTimer = null;
                }
                console.log("[实时图像调整] 已清除所有定时器");
            };

            // 节点移除时清理
            const onRemoved = nodeType.prototype.onRemoved;
            nodeType.prototype.onRemoved = function () {
                const result = onRemoved?.apply(this, arguments);

                // 清除定时器
                this.clearAdjustmentTimers();

                if (this.canvas) {
                    const ctx = this.canvas.getContext("2d");
                    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                    this.canvas = null;
                }

                if (this.tempCanvas) {
                    this.tempCanvas = null;
                }

                this.previewElement = null;
                this.originalImageData = null;
                this.finalImageData = null;

                console.log(`[实时图像调整] 节点 ${this.id} 已清理`);

                return result;
            };
        }
    }
});

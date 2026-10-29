import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function toggleWidgetVisibility(node, widget, visible) {
    if (!widget) return;
    if (!widget._origType) {
        widget._origType = widget.type;
        widget._origComputeSize = widget.computeSize;
    }
    if (visible) {
        widget.type = widget._origType;
        widget.computeSize = widget._origComputeSize;
        widget.hidden = false;
    } else {
        widget.type = "hidden";
        widget.computeSize = () => [0, -4];
        widget.hidden = true;
    }
}

app.registerExtension({
    name: "salvatore.FastVideoGenerate",

    async setup() {
        api.addEventListener("salvatore.fastvideo.status", (event) => {
            const detail = event.detail || {};
            const nodeId = String(detail.node_id || "");
            if (!nodeId || !app.graph) return;

            const node = app.graph.getNodeById(Number(nodeId)) || app.graph.getNodeById(nodeId);
            if (!node) return;

            node._fastvideoStatusMessage = detail.message || "";
            node._fastvideoJobId = detail.job_id || "";
            node._fastvideoState = detail.state || "";
            if (node._fastvideoStatusEl) {
                node._fastvideoStatusEl.textContent = node._fastvideoStatusMessage;
                node._fastvideoStatusEl.style.display = node._fastvideoStatusMessage ? "block" : "none";
            }
            app.graph.setDirtyCanvas(true, true);
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "FastVideoGenerate") {
            return;
        }

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : undefined;

            const baseUrlWidget = this.widgets?.find((w) => w.name === "base_url");
            const apiKeyWidget = this.widgets?.find((w) => w.name === "api_key");
            const modelWidget = this.widgets?.find((w) => w.name === "model");
            const sizeWidget = this.widgets?.find((w) => w.name === "size");
            const widthWidget = this.widgets?.find((w) => w.name === "width");
            const heightWidget = this.widgets?.find((w) => w.name === "height");

            const syncResolutionWidgets = () => {
                if (!sizeWidget) return;
                const val = String(sizeWidget.value || "");
                const isCustom = val.toLowerCase().startsWith("custom");
                const match = val.match(/^(\d+)x(\d+)\b/);
                if (match && widthWidget && heightWidget) {
                    widthWidget.value = Number(match[1]);
                    heightWidget.value = Number(match[2]);
                }
                toggleWidgetVisibility(this, widthWidget, isCustom);
                toggleWidgetVisibility(this, heightWidget, isCustom);
                this.setSize([this.size[0], this.computeSize()[1]]);
                app.graph?.setDirtyCanvas(true, true);
            };

            if (sizeWidget) {
                const origSizeCallback = sizeWidget.callback;
                sizeWidget.callback = (value) => {
                    if (typeof origSizeCallback === "function") {
                        origSizeCallback.call(sizeWidget, value);
                    }
                    syncResolutionWidgets();
                };
                setTimeout(() => syncResolutionWidgets(), 0);
            }

            const origOnConfigure = this.onConfigure;
            this.onConfigure = function () {
                const r = origOnConfigure ? origOnConfigure.apply(this, arguments) : undefined;
                syncResolutionWidgets();
                return r;
            };

            // Add a button to populate `model` from GET /v1/models while keeping `model` manually editable
            const refreshBtn = this.addWidget("button", "Refresh Model (/v1/models)", null, async () => {
                const baseUrl = baseUrlWidget ? baseUrlWidget.value : "http://127.0.0.1:8000/v1";
                const apiKey = apiKeyWidget ? apiKeyWidget.value : "";

                if (this._fastvideoStatusEl) {
                    this._fastvideoStatusEl.textContent = "Querying GET /v1/models…";
                    this._fastvideoStatusEl.style.display = "block";
                }

                try {
                    const resp = await api.fetchApi("/salvatore/fastvideo/models", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
                    });
                    const data = await resp.json();
                    if (resp.ok && data.status === "ok" && Array.isArray(data.models) && data.models.length > 0) {
                        if (modelWidget) {
                            modelWidget.value = data.models[0];
                            if (typeof modelWidget.callback === "function") {
                                modelWidget.callback(modelWidget.value);
                            }
                        }
                        if (this._fastvideoStatusEl) {
                            this._fastvideoStatusEl.textContent = `Served model: ${data.models.join(", ")}`;
                            this._fastvideoStatusEl.style.display = "block";
                        }
                    } else {
                        const errMsg = data.message || "No models returned from /v1/models";
                        if (this._fastvideoStatusEl) {
                            this._fastvideoStatusEl.textContent = `Error: ${errMsg}`;
                            this._fastvideoStatusEl.style.display = "block";
                        }
                    }
                } catch (err) {
                    if (this._fastvideoStatusEl) {
                        this._fastvideoStatusEl.textContent = `Connection error: ${err.message || err}`;
                        this._fastvideoStatusEl.style.display = "block";
                    }
                }
                app.graph?.setDirtyCanvas(true, true);
            });
            refreshBtn.serialize = false;

            // Indeterminate status banner element
            if (typeof document !== "undefined" && typeof this.addDOMWidget === "function") {
                const statusEl = document.createElement("div");
                statusEl.style.cssText =
                    "font-family: monospace; font-size: 11px; padding: 4px 6px; " +
                    "border-radius: 4px; background: rgba(0,0,0,0.35); color: #d6e4ff; " +
                    "white-space: pre-wrap; word-break: break-word; display: none;";
                this._fastvideoStatusEl = statusEl;
                const domWidget = this.addDOMWidget("fastvideo_status", "div", statusEl, {
                    serialize: false,
                    hideOnZoom: false,
                });
                domWidget.computeSize = (width) => [width, this._fastvideoStatusMessage ? 28 : 0];
            }

            return result;
        };
    },
});

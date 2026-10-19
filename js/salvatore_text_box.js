import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

/**
 * Lightweight, safe Markdown-to-HTML parser for SalvatoreTextBox.
 */
function renderMarkdownToHtml(markdownText) {
    if (!markdownText) {
        return '<span class="salvatore-md-placeholder">Empty text...</span>';
    }

    // Escape HTML entities first to prevent XSS
    let text = String(markdownText)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Extract fenced code blocks first so their contents aren't parsed as inline markdown
    const codeBlocks = [];
    text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
        const index = codeBlocks.length;
        const langLabel = lang ? `<div class="salvatore-md-code-lang">${lang}</div>` : "";
        codeBlocks.push(
            `<div class="salvatore-md-codeblock">${langLabel}<pre><code>${code.replace(/\n$/, "")}</code></pre></div>`
        );
        return `\x00CODEBLOCK_${index}\x00`;
    });

    // Extract inline code spans
    const inlineCodes = [];
    text = text.replace(/`([^`\n]+)`/g, (_, code) => {
        const index = inlineCodes.length;
        inlineCodes.push(`<code class="salvatore-md-inline-code">${code}</code>`);
        return `\x00INLINECODE_${index}\x00`;
    });

    const formatInline = (line) => {
        let out = line;
        // Bold + Italic
        out = out.replace(/\*\*\*([^\*]+)\*\*\*/g, "<strong><em>$1</em></strong>");
        out = out.replace(/___([^_]+)___/g, "<strong><em>$1</em></strong>");
        // Bold
        out = out.replace(/\*\*([^\*]+)\*\*/g, "<strong>$1</strong>");
        out = out.replace(/__([^_]+)__/g, "<strong>$1</strong>");
        // Italic
        out = out.replace(/\*([^\*\n]+)\*/g, "<em>$1</em>");
        out = out.replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,!?:;]|$)/g, "$1<em>$2</em>");
        // Strikethrough
        out = out.replace(/~~([^~]+)~~/g, "<del>$1</del>");
        // Links [label](url)
        out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        // Restore inline code spans
        out = out.replace(/\x00INLINECODE_(\d+)\x00/g, (_, idx) => inlineCodes[Number(idx)] || "");
        return out;
    };

    const lines = text.split(/\r?\n/);
    const htmlParts = [];
    let inUl = false;
    let inOl = false;
    let inBlockquote = false;
    let inTable = false;

    const closeListsAndBlocks = () => {
        if (inUl) {
            htmlParts.push("</ul>");
            inUl = false;
        }
        if (inOl) {
            htmlParts.push("</ol>");
            inOl = false;
        }
        if (inBlockquote) {
            htmlParts.push("</blockquote>");
            inBlockquote = false;
        }
        if (inTable) {
            htmlParts.push("</tbody></table>");
            inTable = false;
        }
    };

    for (let i = 0; i < lines.length; i++) {
        const rawLine = lines[i];
        const trimmed = rawLine.trim();

        // Code block placeholder
        const codeMatch = trimmed.match(/^\x00CODEBLOCK_(\d+)\x00$/);
        if (codeMatch) {
            closeListsAndBlocks();
            htmlParts.push(codeBlocks[Number(codeMatch[1])] || "");
            continue;
        }

        // Empty line
        if (trimmed === "") {
            closeListsAndBlocks();
            continue;
        }

        // Horizontal rule
        if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) {
            closeListsAndBlocks();
            htmlParts.push("<hr />");
            continue;
        }

        // Headings (# through ######)
        const headingMatch = rawLine.match(/^\s*(#{1,6})\s+(.*)$/);
        if (headingMatch) {
            closeListsAndBlocks();
            const level = headingMatch[1].length;
            htmlParts.push(`<h${level}>${formatInline(headingMatch[2])}</h${level}>`);
            continue;
        }

        // Blockquote
        const quoteMatch = rawLine.match(/^\s*&gt;\s?(.*)$/);
        if (quoteMatch) {
            if (inUl) { htmlParts.push("</ul>"); inUl = false; }
            if (inOl) { htmlParts.push("</ol>"); inOl = false; }
            if (inTable) { htmlParts.push("</tbody></table>"); inTable = false; }
            if (!inBlockquote) {
                htmlParts.push("<blockquote>");
                inBlockquote = true;
            }
            htmlParts.push(`<div>${formatInline(quoteMatch[1])}</div>`);
            continue;
        } else if (inBlockquote) {
            htmlParts.push("</blockquote>");
            inBlockquote = false;
        }

        // Markdown table row
        if (trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.length > 2) {
            const cells = trimmed
                .slice(1, -1)
                .split("|")
                .map((c) => c.trim());

            // Check if separator row (e.g., |---|---|)
            if (cells.every((c) => /^:?-{2,}:?$/.test(c))) {
                continue;
            }

            if (inUl) { htmlParts.push("</ul>"); inUl = false; }
            if (inOl) { htmlParts.push("</ol>"); inOl = false; }

            if (!inTable) {
                htmlParts.push('<table class="salvatore-md-table"><thead><tr>');
                cells.forEach((c) => htmlParts.push(`<th>${formatInline(c)}</th>`));
                htmlParts.push("</tr></thead><tbody>");
                inTable = true;
            } else {
                htmlParts.push("<tr>");
                cells.forEach((c) => htmlParts.push(`<td>${formatInline(c)}</td>`));
                htmlParts.push("</tr>");
            }
            continue;
        } else if (inTable) {
            htmlParts.push("</tbody></table>");
            inTable = false;
        }

        // Unordered list item (-, *, +) with optional task checkbox
        const ulMatch = rawLine.match(/^\s*[-*+]\s+(.*)$/);
        if (ulMatch) {
            if (inOl) { htmlParts.push("</ol>"); inOl = false; }
            if (!inUl) {
                htmlParts.push("<ul>");
                inUl = true;
            }
            let itemText = ulMatch[1];
            const taskMatch = itemText.match(/^\[([ xX])\]\s+(.*)$/);
            if (taskMatch) {
                const checked = taskMatch[1].toLowerCase() === "x" ? "checked" : "";
                htmlParts.push(
                    `<li class="salvatore-md-task"><input type="checkbox" disabled ${checked}/> <span>${formatInline(taskMatch[2])}</span></li>`
                );
            } else {
                htmlParts.push(`<li>${formatInline(itemText)}</li>`);
            }
            continue;
        }

        // Ordered list item (1., 2., etc.)
        const olMatch = rawLine.match(/^\s*\d+\.\s+(.*)$/);
        if (olMatch) {
            if (inUl) { htmlParts.push("</ul>"); inUl = false; }
            if (!inOl) {
                htmlParts.push("<ol>");
                inOl = true;
            }
            htmlParts.push(`<li>${formatInline(olMatch[1])}</li>`);
            continue;
        }

        // Regular paragraph line
        closeListsAndBlocks();
        htmlParts.push(`<p>${formatInline(rawLine)}</p>`);
    }

    closeListsAndBlocks();

    // Restore any remaining code blocks if inline
    return htmlParts
        .join("\n")
        .replace(/\x00CODEBLOCK_(\d+)\x00/g, (_, idx) => codeBlocks[Number(idx)] || "");
}

/**
 * Inject CSS styles once for SalvatoreTextBox.
 */
function ensureStylesInjected() {
    if (document.getElementById("salvatore-text-box-styles")) {
        return;
    }
    const style = document.createElement("style");
    style.id = "salvatore-text-box-styles";
    style.textContent = `
        .salvatore-textbox-root {
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            box-sizing: border-box;
            gap: 6px;
            padding: 4px 2px;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #e4e4e7;
        }
        .salvatore-textbox-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #18181b;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 3px 6px;
            gap: 4px;
            flex-shrink: 0;
        }
        .salvatore-textbox-toolbar-label {
            font-size: 11px;
            color: #a1a1aa;
            font-weight: 600;
            letter-spacing: 0.02em;
            user-select: none;
        }
        .salvatore-textbox-mode-group {
            display: flex;
            gap: 3px;
        }
        .salvatore-textbox-mode-btn {
            background: #27272a;
            color: #d4d4d8;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .salvatore-textbox-mode-btn:hover {
            background: #3f3f46;
            color: #ffffff;
        }
        .salvatore-textbox-mode-btn.active {
            background: #3b82f6;
            border-color: #60a5fa;
            color: #ffffff;
            font-weight: 600;
        }
        .salvatore-textbox-panes {
            display: flex;
            flex-direction: column;
            flex: 1 1 auto;
            min-height: 120px;
            gap: 6px;
            overflow: hidden;
        }
        .salvatore-textbox-textarea {
            flex: 1 1 50%;
            width: 100%;
            min-height: 60px;
            box-sizing: border-box;
            resize: none;
            background: #141417;
            color: #f4f4f5;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 8px 10px;
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
            font-size: 12.5px;
            line-height: 1.45;
            outline: none;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }
        .salvatore-textbox-textarea:focus {
            border-color: #60a5fa;
            box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.35);
        }
        .salvatore-textbox-markdown {
            flex: 1 1 50%;
            width: 100%;
            min-height: 60px;
            box-sizing: border-box;
            overflow-y: auto;
            background: #18181c;
            color: #e4e4e7;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            line-height: 1.5;
            word-wrap: break-word;
        }
        .salvatore-textbox-markdown h1,
        .salvatore-textbox-markdown h2,
        .salvatore-textbox-markdown h3,
        .salvatore-textbox-markdown h4,
        .salvatore-textbox-markdown h5,
        .salvatore-textbox-markdown h6 {
            margin: 0.4em 0 0.25em 0;
            font-weight: 600;
            color: #fafafa;
            line-height: 1.25;
        }
        .salvatore-textbox-markdown h1 { font-size: 1.35em; border-bottom: 1px solid #3f3f46; padding-bottom: 3px; }
        .salvatore-textbox-markdown h2 { font-size: 1.2em; border-bottom: 1px solid #27272a; padding-bottom: 2px; }
        .salvatore-textbox-markdown h3 { font-size: 1.08em; }
        .salvatore-textbox-markdown p {
            margin: 0.35em 0;
        }
        .salvatore-textbox-markdown ul,
        .salvatore-textbox-markdown ol {
            margin: 0.35em 0;
            padding-left: 1.4em;
        }
        .salvatore-textbox-markdown li {
            margin: 0.15em 0;
        }
        .salvatore-textbox-markdown li.salvatore-md-task {
            list-style: none;
            margin-left: -1.1em;
        }
        .salvatore-textbox-markdown blockquote {
            margin: 0.4em 0;
            padding: 4px 10px;
            border-left: 3px solid #60a5fa;
            background: rgba(96, 165, 250, 0.08);
            color: #d4d4d8;
            border-radius: 0 4px 4px 0;
        }
        .salvatore-textbox-markdown hr {
            border: none;
            border-top: 1px solid #3f3f46;
            margin: 8px 0;
        }
        .salvatore-md-inline-code {
            background: #27272a;
            color: #f472b6;
            padding: 1px 5px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.92em;
        }
        .salvatore-md-codeblock {
            background: #09090b;
            border: 1px solid #27272a;
            border-radius: 6px;
            margin: 6px 0;
            overflow: hidden;
        }
        .salvatore-md-code-lang {
            background: #18181b;
            color: #a1a1aa;
            font-size: 10px;
            padding: 2px 8px;
            border-bottom: 1px solid #27272a;
            font-family: monospace;
            text-transform: uppercase;
        }
        .salvatore-md-codeblock pre {
            margin: 0;
            padding: 8px 10px;
            overflow-x: auto;
            font-family: monospace;
            font-size: 12px;
            color: #e4e4e7;
        }
        .salvatore-md-table {
            border-collapse: collapse;
            width: 100%;
            margin: 6px 0;
            font-size: 12px;
        }
        .salvatore-md-table th,
        .salvatore-md-table td {
            border: 1px solid #3f3f46;
            padding: 4px 8px;
            text-align: left;
        }
        .salvatore-md-table th {
            background: #27272a;
            font-weight: 600;
        }
        .salvatore-md-placeholder {
            color: #71717a;
            font-style: italic;
        }
        .salvatore-textbox-confirm-bar {
            display: flex;
            flex-direction: column;
            gap: 4px;
            flex-shrink: 0;
        }
        .salvatore-textbox-status {
            font-size: 11px;
            color: #a1a1aa;
            text-align: center;
            padding: 2px 4px;
            border-radius: 4px;
            display: none;
        }
        .salvatore-textbox-status.waiting {
            display: block;
            color: #fde047;
            background: rgba(234, 179, 8, 0.14);
            border: 1px solid rgba(234, 179, 8, 0.35);
            font-weight: 600;
        }
        .salvatore-textbox-go-btn {
            width: 100%;
            padding: 7px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid #3f3f46;
            background: #27272a;
            color: #e4e4e7;
            transition: all 0.15s ease;
        }
        .salvatore-textbox-go-btn:hover {
            background: #3f3f46;
        }
        .salvatore-textbox-go-btn.waiting {
            background: linear-gradient(135deg, #16a34a, #15803d);
            border-color: #4ade80;
            color: #ffffff;
            box-shadow: 0 0 10px rgba(34, 197, 94, 0.45);
            animation: salvatore-pulse 1.5s infinite ease-in-out;
        }
        .salvatore-textbox-go-btn.waiting:hover {
            background: linear-gradient(135deg, #22c55e, #16a34a);
        }
        @keyframes salvatore-pulse {
            0%, 100% { box-shadow: 0 0 6px rgba(34, 197, 94, 0.4); }
            50% { box-shadow: 0 0 14px rgba(74, 222, 128, 0.8); }
        }
    `;
    document.head.appendChild(style);
}

// Map of node.id -> UI controller for fast WebSocket updates
const nodeControllers = new Map();

app.registerExtension({
    name: "Salvatore.TextBox",

    async setup() {
        ensureStylesInjected();

        // Listen for WebSocket updates from SalvatoreTextBox Python execution
        api.addEventListener("salvatore.text_box.update", (event) => {
            const detail = event.detail;
            if (!detail || detail.node_id === undefined) return;
            const controller = nodeControllers.get(String(detail.node_id));
            if (controller) {
                controller.handleBackendUpdate(detail);
            }
        });

        // Clear any waiting state if workflow execution is interrupted or errors
        const clearAllWaiting = () => {
            for (const controller of nodeControllers.values()) {
                controller.setWaitingState(false);
            }
        };
        api.addEventListener("execution_interrupted", clearAllWaiting);
        api.addEventListener("execution_error", clearAllWaiting);
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "SalvatoreTextBox") {
            return;
        }

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const res = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : undefined;
            const node = this;

            ensureStylesInjected();

            // Locate the underlying widgets generated from INPUT_TYPES
            const textWidget = node.widgets?.find((w) => w.name === "text");
            const renderMarkdownWidget = node.widgets?.find((w) => w.name === "render_markdown");
            const waitConfirmWidget = node.widgets?.find((w) => w.name === "wait_for_confirmation");

            // Hide the raw single-line 'text' canvas widget so only our rich editable DOM widget is shown,
            // while keeping textWidget in node.widgets so ComfyUI serializes its value normally.
            if (textWidget) {
                textWidget.type = "converted-widget";
                textWidget.computeSize = () => [0, -4];
                textWidget.draw = () => {};
            }

            // Build the DOM structure
            const root = document.createElement("div");
            root.className = "salvatore-textbox-root";

            // Markdown mode toolbar (shown when render_markdown is enabled)
            const toolbar = document.createElement("div");
            toolbar.className = "salvatore-textbox-toolbar";

            const toolbarLabel = document.createElement("span");
            toolbarLabel.className = "salvatore-textbox-toolbar-label";
            toolbarLabel.textContent = "Markdown View (Double-click preview to edit)";

            const modeGroup = document.createElement("div");
            modeGroup.className = "salvatore-textbox-mode-group";

            const btnSplit = document.createElement("button");
            btnSplit.type = "button";
            btnSplit.className = "salvatore-textbox-mode-btn active";
            btnSplit.textContent = "Split";

            const btnEdit = document.createElement("button");
            btnEdit.type = "button";
            btnEdit.className = "salvatore-textbox-mode-btn";
            btnEdit.textContent = "Edit";

            const btnPreview = document.createElement("button");
            btnPreview.type = "button";
            btnPreview.className = "salvatore-textbox-mode-btn";
            btnPreview.textContent = "Preview";

            modeGroup.appendChild(btnSplit);
            modeGroup.appendChild(btnEdit);
            modeGroup.appendChild(btnPreview);
            toolbar.appendChild(toolbarLabel);
            toolbar.appendChild(modeGroup);

            // Panes container (editable textarea + rendered markdown preview)
            const panes = document.createElement("div");
            panes.className = "salvatore-textbox-panes";

            const textarea = document.createElement("textarea");
            textarea.className = "salvatore-textbox-textarea";
            textarea.placeholder = "Enter or edit text here...";
            textarea.spellcheck = false;
            textarea.value = textWidget ? String(textWidget.value ?? "") : "";

            // Prevent ComfyUI canvas hotkeys (Delete, Backspace, Space, etc.) from firing while typing
            for (const evtName of ["keydown", "keyup", "keypress"]) {
                textarea.addEventListener(evtName, (e) => {
                    e.stopPropagation();
                });
            }

            const markdownPane = document.createElement("div");
            markdownPane.className = "salvatore-textbox-markdown";
            markdownPane.title = "Double-click to switch to Edit mode";

            panes.appendChild(textarea);
            panes.appendChild(markdownPane);

            // Confirm ("Go") button container (shown when wait_for_confirmation is enabled)
            const confirmBar = document.createElement("div");
            confirmBar.className = "salvatore-textbox-confirm-bar";

            const statusBanner = document.createElement("div");
            statusBanner.className = "salvatore-textbox-status";
            statusBanner.textContent = "⏸ Waiting for confirmation — edit text if needed, then press Go";

            const goButton = document.createElement("button");
            goButton.type = "button";
            goButton.className = "salvatore-textbox-go-btn";
            goButton.textContent = "▶ Go";

            confirmBar.appendChild(statusBanner);
            confirmBar.appendChild(goButton);

            root.appendChild(toolbar);
            root.appendChild(panes);
            root.appendChild(confirmBar);

            // State
            let mdViewMode = "split"; // "split" | "edit" | "preview"
            let isWaiting = false;

            const updateMarkdownPreview = () => {
                markdownPane.innerHTML = renderMarkdownToHtml(textarea.value);
            };

            const syncTextToWidget = (newText) => {
                if (textarea.value !== newText) {
                    textarea.value = newText;
                }
                if (textWidget) {
                    textWidget.value = newText;
                }
                updateMarkdownPreview();
            };

            const updateLayoutVisibility = () => {
                const renderMd = Boolean(renderMarkdownWidget?.value);
                const waitConfirm = Boolean(waitConfirmWidget?.value);

                toolbar.style.display = renderMd ? "flex" : "none";

                if (!renderMd) {
                    textarea.style.display = "block";
                    markdownPane.style.display = "none";
                } else {
                    btnSplit.classList.toggle("active", mdViewMode === "split");
                    btnEdit.classList.toggle("active", mdViewMode === "edit");
                    btnPreview.classList.toggle("active", mdViewMode === "preview");

                    textarea.style.display = mdViewMode === "preview" ? "none" : "block";
                    markdownPane.style.display = mdViewMode === "edit" ? "none" : "block";
                    updateMarkdownPreview();
                }

                confirmBar.style.display = waitConfirm || isWaiting ? "flex" : "none";
            };

            const setWaitingState = (waiting) => {
                isWaiting = Boolean(waiting);
                goButton.classList.toggle("waiting", isWaiting);
                statusBanner.classList.toggle("waiting", isWaiting);
                goButton.textContent = isWaiting ? "▶ Go (Confirm & Continue)" : "▶ Go";
                updateLayoutVisibility();
            };

            // Event listeners for mode buttons
            btnSplit.addEventListener("click", () => {
                mdViewMode = "split";
                updateLayoutVisibility();
            });
            btnEdit.addEventListener("click", () => {
                mdViewMode = "edit";
                updateLayoutVisibility();
                textarea.focus();
            });
            btnPreview.addEventListener("click", () => {
                mdViewMode = "preview";
                updateLayoutVisibility();
            });
            markdownPane.addEventListener("dblclick", () => {
                mdViewMode = "edit";
                updateLayoutVisibility();
                textarea.focus();
            });

            // Sync edits in textarea back to the ComfyUI widget and live Markdown preview
            textarea.addEventListener("input", () => {
                if (textWidget) {
                    textWidget.value = textarea.value;
                }
                if (renderMarkdownWidget?.value) {
                    updateMarkdownPreview();
                }
            });

            // Confirm ("Go") button click handler
            goButton.addEventListener("click", async () => {
                const currentText = textarea.value;
                syncTextToWidget(currentText);

                try {
                    const response = await api.fetchApi("/salvatore/text_confirm", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            node_id: String(node.id),
                            text: currentText,
                            action: "confirm",
                        }),
                    });
                    if (response.ok) {
                        setWaitingState(false);
                    }
                } catch (err) {
                    console.error("[SalvatoreTextBox] Failed to send confirmation:", err);
                }
            });

            // Hook into boolean toggle changes so UI updates immediately when toggled by user
            if (renderMarkdownWidget) {
                const origMdCallback = renderMarkdownWidget.callback;
                renderMarkdownWidget.callback = function () {
                    if (origMdCallback) origMdCallback.apply(this, arguments);
                    updateLayoutVisibility();
                };
            }
            if (waitConfirmWidget) {
                const origWaitCallback = waitConfirmWidget.callback;
                waitConfirmWidget.callback = function () {
                    if (origWaitCallback) origWaitCallback.apply(this, arguments);
                    updateLayoutVisibility();
                };
            }

            // Add the DOM widget to the node
            const domWidget = node.addDOMWidget("salvatore_textbox_ui", "div", root, {
                serialize: false,
                hideOnZoom: false,
            });
            domWidget.serialize = false;

            // Ensure comfortable initial node size
            if (!node.size || node.size[0] < 340 || node.size[1] < 280) {
                node.setSize([Math.max(node.size?.[0] || 0, 360), Math.max(node.size?.[1] || 0, 300)]);
            }

            // Register controller for WebSocket events
            const registerController = () => {
                if (node.id !== undefined && node.id !== -1) {
                    nodeControllers.set(String(node.id), {
                        handleBackendUpdate(detail) {
                            if (typeof detail.text === "string") {
                                syncTextToWidget(detail.text);
                            }
                            setWaitingState(Boolean(detail.waiting));
                        },
                        setWaitingState,
                        syncTextToWidget,
                    });
                }
            };
            registerController();

            // Keep controller registered when node ID is assigned/configured
            const origOnAdded = node.onAdded;
            node.onAdded = function () {
                if (origOnAdded) origOnAdded.apply(this, arguments);
                registerController();
            };

            const origOnConfigure = node.onConfigure;
            node.onConfigure = function () {
                if (origOnConfigure) origOnConfigure.apply(this, arguments);
                registerController();
                if (textWidget && typeof textWidget.value === "string") {
                    textarea.value = textWidget.value;
                }
                updateMarkdownPreview();
                updateLayoutVisibility();
            };

            const origOnExecuted = node.onExecuted;
            node.onExecuted = function (output) {
                if (origOnExecuted) origOnExecuted.apply(this, arguments);
                if (output && Array.isArray(output.text) && output.text.length > 0) {
                    syncTextToWidget(String(output.text[0]));
                }
                setWaitingState(false);
            };

            const origOnRemoved = node.onRemoved;
            node.onRemoved = function () {
                if (origOnRemoved) origOnRemoved.apply(this, arguments);
                if (node.id !== undefined) {
                    nodeControllers.delete(String(node.id));
                }
            };

            updateMarkdownPreview();
            updateLayoutVisibility();

            return res;
        };
    },
});

import { api } from "../api.js";
import { state } from "../state.js";
import { connectToThread, sendMessage, onWsMessage } from "../ws.js";
import { navigate } from "../router.js";
import { renderMarkdown, initDiagrams, enhanceCodeBlocks } from "../markdown.js";

let thinkingEl = null;
let streamingAiBubble = null;
let pendingAttachment = null; // { id, filename, content_type, url, is_image }

export async function renderChat(groupId, threadId) {
  const thread = state.threads.find((t) => t.id === parseInt(threadId));
  const main = document.querySelector(".main-panel");
  if (!main) return;

  main.innerHTML = `
    <div class="chat-header">
      <h3>${thread ? "# " + thread.title : "Loading…"}</h3>
      <div class="header-actions">
        <button class="btn btn-ghost btn-sm" id="view-plan-btn">View Plan</button>
        <button class="btn btn-ghost btn-sm" id="view-docs-btn">Docs</button>
      </div>
    </div>
    <div class="message-list" id="message-list"></div>
    <div class="chat-input-area">
      <div class="attachment-preview" id="attachment-preview" style="display:none"></div>
      <div class="chat-input-row">
        <button class="icon-btn" id="attach-btn" title="Attach file">📎</button>
        <input type="file" id="file-input" style="display:none"
          accept="image/*,.pdf,.txt,.md,.csv,.json" />
        <textarea class="chat-input" id="chat-input" rows="1"
          placeholder="Message… type @ai to ask the AI"></textarea>
        <button class="btn btn-primary" id="send-btn">Send</button>
      </div>
      <div class="chat-hint">Tip: type <span class="ai-mention">@ai</span> to get AI help with planning · 📎 attach images, PDFs, or text files</div>
    </div>
  `;

  // Load history
  state.messages = await api.getMessages(threadId);
  _renderMessages(state.messages);

  // Connect WebSocket
  connectToThread(parseInt(threadId));
  onWsMessage((msg) => {
    if (msg.type === "ai_thinking") {
      _showThinking();
    } else if (msg.type === "ai_delta") {
      _removeThinking();
      _appendAiDelta(msg.token);
    } else if (msg.type === "ai_message_complete") {
      _finalizeAiStream(msg);
      state.messages.push(msg);
    } else if (msg.type === "message") {
      _removeThinking();
      state.messages.push(msg);
      _appendMessage(msg);
    }
  });

  // Send button
  document.getElementById("send-btn").addEventListener("click", _sendMessage);
  document.getElementById("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      _sendMessage();
    }
  });

  // Auto-resize textarea
  document.getElementById("chat-input").addEventListener("input", (e) => {
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  });

  // Plan button
  document.getElementById("view-plan-btn").addEventListener("click", () => {
    navigate(`/groups/${groupId}/threads/${threadId}/plan`);
  });

  document.getElementById("view-docs-btn").addEventListener("click", () => {
    navigate(`/groups/${groupId}/threads/${threadId}/docs`);
  });

  // File upload
  document.getElementById("attach-btn").addEventListener("click", () => {
    document.getElementById("file-input").click();
  });

  document.getElementById("file-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const btn = document.getElementById("attach-btn");
    btn.textContent = "⏳";
    btn.disabled = true;
    try {
      const att = await api.uploadFile(threadId, file);
      pendingAttachment = att;
      _showAttachmentPreview(att);
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      btn.textContent = "📎";
      btn.disabled = false;
      e.target.value = "";
    }
  });
}

function _sendMessage() {
  const input = document.getElementById("chat-input");
  const content = input.value.trim();
  if (!content && !pendingAttachment) return;
  const text = content || (pendingAttachment ? `@ai what do you see in this file?` : "");
  sendMessage(text, pendingAttachment?.id || null);
  input.value = "";
  input.style.height = "auto";
  pendingAttachment = null;
  _clearAttachmentPreview();
}

function _renderMessages(messages) {
  const list = document.getElementById("message-list");
  if (!list) return;
  list.innerHTML = messages.length
    ? messages.map(_messageHTML).join("")
    : `<div class="empty-state"><div class="empty-icon">💬</div><p>No messages yet.<br/>Start the conversation!</p></div>`;
  list.scrollTop = list.scrollHeight;
  // Render diagrams in AI messages
  list.querySelectorAll(".message.ai").forEach((el) => initDiagrams(el));
  list.querySelectorAll(".message.ai").forEach((el) => enhanceCodeBlocks(el));
  // Wire up edit buttons
  list.querySelectorAll(".msg-edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => _startEdit(parseInt(btn.dataset.id)));
  });
}

function _appendMessage(msg) {
  const list = document.getElementById("message-list");
  if (!list) return;
  const empty = list.querySelector(".empty-state");
  if (empty) empty.remove();
  list.insertAdjacentHTML("beforeend", _messageHTML(msg));
  if (msg.is_ai) {
    const last = list.lastElementChild;
    initDiagrams(last);
    enhanceCodeBlocks(last);
  }
  list.scrollTop = list.scrollHeight;
}

function _messageHTML(msg) {
  const isOwn = msg.user_id === state.user?.id;
  const cls = msg.is_ai ? "ai" : isOwn ? "self" : "other";
  const name = msg.is_ai ? "GroupThink AI" : (msg.username || "Unknown");
  const time = new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const isAI = msg.is_ai;
  const content = isAI ? renderMarkdown(msg.content) : _escapeHtml(msg.content);
  const bubbleClass = isAI ? "message-bubble markdown-body" : "message-bubble";
  const attachmentsHTML = (msg.attachments || []).map((att) => {
    if (att.is_image) {
      return `<div class="msg-attachment"><img src="${att.url}" alt="${_escapeHtml(att.filename)}" class="msg-img" loading="lazy" /></div>`;
    }
    return `<div class="msg-attachment"><a href="${att.url}" target="_blank" class="msg-file-chip">${_fileIcon(att.content_type)} ${_escapeHtml(att.filename)}</a></div>`;
  }).join("");
  const editBtn = !isAI && isOwn
    ? `<div class="msg-actions"><button class="msg-edit-btn" data-id="${msg.id}">Edit</button></div>`
    : "";
  return `
    <div class="message ${cls}" data-msg-id="${msg.id}">
      <div class="message-meta">
        <span class="username">${_escapeHtml(name)}</span>
        <span>${time}</span>
      </div>
      ${attachmentsHTML}
      <div class="${bubbleClass}">${content}</div>
      ${editBtn}
    </div>
  `;
}

function _appendAiDelta(token) {
  const list = document.getElementById("message-list");
  if (!list) return;

  if (!streamingAiBubble) {
    // Create streaming bubble
    const el = document.createElement("div");
    el.className = "message ai";
    el.innerHTML = `
      <div class="message-meta">
        <span class="username" style="color:var(--color-accent)">GroupThink AI</span>
      </div>
      <div class="message-bubble markdown-body streaming-content"></div>
    `;
    list.appendChild(el);
    streamingAiBubble = el;
  }

  const bubble = streamingAiBubble.querySelector(".streaming-content");
  if (bubble) {
    bubble._rawText = (bubble._rawText || "") + token;
    bubble.innerHTML = renderMarkdown(bubble._rawText) + '<span class="cursor-blink">▋</span>';
  }
  list.scrollTop = list.scrollHeight;
}

function _finalizeAiStream(msg) {
  if (streamingAiBubble) {
    const bubble = streamingAiBubble.querySelector(".streaming-content");
    if (bubble) {
      bubble.innerHTML = renderMarkdown(msg.content);
      bubble.className = "message-bubble markdown-body";
    }
    // Add timestamp to meta
    const meta = streamingAiBubble.querySelector(".message-meta");
    if (meta) {
      const time = new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      meta.insertAdjacentHTML("beforeend", `<span>${time}</span>`);
    }
    initDiagrams(streamingAiBubble);
    enhanceCodeBlocks(streamingAiBubble);
    streamingAiBubble = null;
  }
  const list = document.getElementById("message-list");
  if (list) list.scrollTop = list.scrollHeight;
}

function _showAttachmentPreview(att) {
  const el = document.getElementById("attachment-preview");
  if (!el) return;
  el.style.display = "flex";
  el.innerHTML = att.is_image
    ? `<div class="att-chip att-chip-img">
        <img src="${att.url}" alt="${_escapeHtml(att.filename)}" />
        <span>${_escapeHtml(att.filename)}</span>
        <button class="att-remove" id="att-remove-btn">×</button>
       </div>`
    : `<div class="att-chip">
        <span class="att-icon">${_fileIcon(att.content_type)}</span>
        <span>${_escapeHtml(att.filename)}</span>
        <button class="att-remove" id="att-remove-btn">×</button>
       </div>`;
  document.getElementById("att-remove-btn").addEventListener("click", () => {
    pendingAttachment = null;
    _clearAttachmentPreview();
  });
}

function _clearAttachmentPreview() {
  const el = document.getElementById("attachment-preview");
  if (el) { el.style.display = "none"; el.innerHTML = ""; }
}

function _fileIcon(contentType) {
  if (contentType === "application/pdf") return "📄";
  if (contentType.startsWith("image/")) return "🖼";
  if (contentType.startsWith("text/")) return "📝";
  return "📎";
}

function _startEdit(messageId) {
  const msgEl = document.querySelector(`[data-msg-id="${messageId}"]`);
  if (!msgEl) return;
  const bubble = msgEl.querySelector(".message-bubble");
  const original = bubble.innerText;
  bubble.innerHTML = `
    <textarea class="edit-textarea">${_escapeHtml(original)}</textarea>
    <div class="edit-actions">
      <button class="btn btn-primary btn-sm" id="edit-save-${messageId}">Save</button>
      <button class="btn btn-ghost btn-sm" id="edit-cancel-${messageId}">Cancel</button>
    </div>
  `;
  bubble.querySelector("textarea").focus();

  document.getElementById(`edit-cancel-${messageId}`).addEventListener("click", () => {
    bubble.innerHTML = _escapeHtml(original);
    bubble.style.whiteSpace = "pre-wrap";
  });

  document.getElementById(`edit-save-${messageId}`).addEventListener("click", async () => {
    const newContent = bubble.querySelector("textarea").value.trim();
    if (!newContent) return;
    try {
      await api.editMessage(messageId, newContent);
      bubble.innerHTML = _escapeHtml(newContent);
      bubble.style.whiteSpace = "pre-wrap";
    } catch (e) {
      alert("Edit failed: " + e.message);
    }
  });
}

function _showThinking() {
  const list = document.getElementById("message-list");
  if (!list || thinkingEl) return;
  thinkingEl = document.createElement("div");
  thinkingEl.className = "ai-thinking";
  thinkingEl.innerHTML = `
    <span>GroupThink AI is thinking</span>
    <div class="dot-pulse"><span></span><span></span><span></span></div>
  `;
  list.appendChild(thinkingEl);
  list.scrollTop = list.scrollHeight;
}

function _removeThinking() {
  if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
}

function _escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

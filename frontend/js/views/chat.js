import { api } from "../api.js";
import { state } from "../state.js";
import { connectToThread, sendMessage, onWsMessage } from "../ws.js";
import { navigate } from "../router.js";
import { renderMarkdown, initDiagrams, enhanceCodeBlocks } from "../markdown.js";

let thinkingEl = null;
let streamingAiBubble = null;

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
      <div class="chat-input-row">
        <textarea class="chat-input" id="chat-input" rows="1"
          placeholder="Message… type @ai to ask the AI"></textarea>
        <button class="btn btn-primary" id="send-btn">Send</button>
      </div>
      <div class="chat-hint">Tip: type <span class="ai-mention">@ai</span> to get AI help with planning</div>
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
}

function _sendMessage() {
  const input = document.getElementById("chat-input");
  const content = input.value.trim();
  if (!content) return;
  sendMessage(content);
  input.value = "";
  input.style.height = "auto";
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
  return `
    <div class="message ${cls}">
      <div class="message-meta">
        <span class="username">${_escapeHtml(name)}</span>
        <span>${time}</span>
      </div>
      <div class="${bubbleClass}">${content}</div>
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

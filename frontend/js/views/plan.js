import { api } from "../api.js";
import { state } from "../state.js";
import { navigate } from "../router.js";
import { renderMarkdown, initDiagrams } from "../markdown.js";

export async function renderPlan(groupId, threadId) {
  const main = document.querySelector(".main-panel");
  if (!main) return;

  main.innerHTML = `
    <div class="chat-header">
      <h3>Plan Designer</h3>
      <div class="header-actions">
        <button class="btn btn-ghost btn-sm" id="back-btn">← Back to Chat</button>
      </div>
    </div>
    <div class="plan-split">
      <!-- Left: live plan document -->
      <div class="plan-doc" id="plan-doc">
        <div class="plan-doc-header">
          <span>Structured Plan</span>
          <span class="plan-generated-at" id="plan-timestamp"></span>
        </div>
        <div id="plan-doc-body">
          <div class="empty-state" style="height:200px">
            <p>Start a conversation to build your plan.</p>
          </div>
        </div>
      </div>

      <!-- Right: AI conversation -->
      <div class="plan-chat-panel">
        <div class="plan-chat-header">
          <span>AI Plan Assistant</span>
          <span style="font-size:11px;color:var(--color-text-muted)">Like Claude, but for your plan</span>
        </div>
        <div class="plan-chat-messages" id="plan-chat-messages">
          <div class="plan-chat-intro">
            <strong>GroupThink AI</strong>
            <p>I'm here to help you design your plan. Tell me what you're working on — goals, constraints, who's involved — and I'll help you structure it into something actionable.</p>
            <p style="margin-top:8px;color:var(--color-text-muted)">All conversation and plan updates are saved and visible to everyone in your group.</p>
          </div>
        </div>
        <div class="plan-chat-input-area">
          <textarea class="plan-chat-input" id="plan-chat-input" rows="2"
            placeholder="Describe your plan, ask questions, or refine details…"></textarea>
          <button class="btn btn-primary" id="plan-chat-send" style="margin-top:8px;width:100%">
            Send
          </button>
        </div>
      </div>
    </div>
  `;

  document.getElementById("back-btn").addEventListener("click", () => {
    navigate(`/groups/${groupId}/threads/${threadId}`);
  });

  // Load existing plan and chat history in parallel
  const [planResult, chatHistory] = await Promise.allSettled([
    api.getPlan(threadId),
    api.getPlanChat(threadId),
  ]);

  if (planResult.status === "fulfilled") {
    _renderPlanDoc(planResult.value);
  }
  if (chatHistory.status === "fulfilled" && chatHistory.value.length) {
    _renderChatHistory(chatHistory.value);
  }

  // Send handler
  document.getElementById("plan-chat-send").addEventListener("click", () => _sendMessage(threadId));
  document.getElementById("plan-chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      _sendMessage(threadId);
    }
  });
  document.getElementById("plan-chat-input").addEventListener("input", (e) => {
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
  });
}

async function _sendMessage(threadId) {
  const input = document.getElementById("plan-chat-input");
  const btn = document.getElementById("plan-chat-send");
  const content = input.value.trim();
  if (!content) return;

  // Optimistically show user message
  _appendChatMessage({ role: "user", content, username: state.user?.username });
  input.value = "";
  input.style.height = "auto";
  btn.disabled = true;
  btn.textContent = "Thinking…";

  // Show typing indicator
  const typingId = _showTyping();

  try {
    const res = await api.sendPlanChat(threadId, content);
    _removeTyping(typingId);
    _appendChatMessage({ role: "assistant", content: res.ai_message.content, username: "GroupThink AI" });
    if (res.plan) _renderPlanDoc(res.plan);
  } catch (e) {
    _removeTyping(typingId);
    _appendChatMessage({ role: "assistant", content: `Error: ${e.message}`, username: "GroupThink AI", isError: true });
  } finally {
    btn.disabled = false;
    btn.textContent = "Send";
  }
}

function _renderChatHistory(messages) {
  const container = document.getElementById("plan-chat-messages");
  if (!container) return;
  messages.forEach((msg) => _appendChatMessage(msg));
}

function _appendChatMessage({ role, content, username, isError }) {
  const container = document.getElementById("plan-chat-messages");
  if (!container) return;
  const isAI = role === "assistant";
  const el = document.createElement("div");
  el.className = `plan-chat-msg ${isAI ? "plan-chat-ai" : "plan-chat-user"}`;
  const bubbleContent = isAI ? renderMarkdown(content) : _esc(content);
  const bubbleClass = `plan-chat-msg-bubble${isAI ? " markdown-body" : ""}${isError ? " plan-chat-error" : ""}`;
  el.innerHTML = `
    <div class="plan-chat-msg-name">${_esc(username || (isAI ? "GroupThink AI" : "You"))}</div>
    <div class="${bubbleClass}">${bubbleContent}</div>
  `;
  container.appendChild(el);
  if (isAI) initDiagrams(el);
  container.scrollTop = container.scrollHeight;
}

function _showTyping() {
  const container = document.getElementById("plan-chat-messages");
  if (!container) return null;
  const id = "typing-" + Date.now();
  const el = document.createElement("div");
  el.id = id;
  el.className = "plan-chat-msg plan-chat-ai";
  el.innerHTML = `
    <div class="plan-chat-msg-name">GroupThink AI</div>
    <div class="plan-chat-msg-bubble ai-thinking">
      <div class="dot-pulse"><span></span><span></span><span></span></div>
    </div>
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return id;
}

function _removeTyping(id) {
  if (id) document.getElementById(id)?.remove();
}

function _renderPlanDoc(plan) {
  const body = document.getElementById("plan-doc-body");
  const ts = document.getElementById("plan-timestamp");
  if (!body) return;

  if (ts && plan.generated_at) {
    ts.textContent = "Updated " + new Date(plan.generated_at).toLocaleString();
  }

  const hasContent = plan.goals?.length || plan.action_items?.length || plan.decisions?.length || plan.summary;
  if (!hasContent) {
    body.innerHTML = `<div class="empty-state" style="height:200px"><p>Keep chatting — the plan will appear here.</p></div>`;
    return;
  }

  body.innerHTML = `
    ${plan.summary ? `<div class="plan-summary markdown-body">${renderMarkdown(plan.summary)}</div>` : ""}

    ${plan.goals?.length ? `
      <div class="plan-section goals">
        <div class="plan-section-header"><span class="section-icon">🎯</span> Goals</div>
        <div class="plan-section-list">
          ${plan.goals.map((g) => `
            <div class="plan-item">
              <div class="plan-item-dot"></div>
              <span>${_esc(g)}</span>
            </div>`).join("")}
        </div>
      </div>` : ""}

    ${plan.action_items?.length ? `
      <div class="plan-section">
        <div class="plan-section-header"><span class="section-icon">✅</span> Action Items</div>
        <div class="plan-section-list">
          ${plan.action_items.map((a) => `
            <div class="action-item">
              <div class="action-checkbox"></div>
              <div class="action-content">
                <div class="action-task">${_esc(a.task)}</div>
                ${(a.assignee || a.due_date) ? `
                  <div class="action-meta">
                    ${a.assignee ? `<span class="assignee">${_esc(a.assignee)}</span>` : ""}
                    ${a.due_date ? `<span>${_esc(a.due_date)}</span>` : ""}
                  </div>` : ""}
              </div>
            </div>`).join("")}
        </div>
      </div>` : ""}

    ${plan.decisions?.length ? `
      <div class="plan-section decisions">
        <div class="plan-section-header"><span class="section-icon">⚡</span> Decisions Made</div>
        <div class="plan-section-list">
          ${plan.decisions.map((d) => `
            <div class="plan-item">
              <div class="plan-item-dot"></div>
              <span>${_esc(d)}</span>
            </div>`).join("")}
        </div>
      </div>` : ""}
  `;
}

function _esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

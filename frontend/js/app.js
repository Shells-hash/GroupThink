import { state, setUser, setToken, loadToken } from "./state.js";
import { api } from "./api.js";
import { route, navigate, initRouter } from "./router.js";
import { renderLogin, renderRegister, renderForgotPassword, renderResetPassword } from "./views/auth.js";
import { renderGroupsSidebar, showCreateGroupModal } from "./views/groups.js";
import { renderThreadSidebar, showCreateThreadModal } from "./views/thread-list.js";
import { renderChat } from "./views/chat.js";
import { renderPlan } from "./views/plan.js";
import { renderDocs } from "./views/docs.js";
import { disconnectWs } from "./ws.js";

// ── App shell template ──────────────────────────────────────────────────────
function renderShell() {
  document.getElementById("app").innerHTML = `
    <div class="app-shell">
      <div class="sidebar-groups">
        <div class="sidebar-header">
          <h2>Groups</h2>
          <button class="icon-btn" id="new-group-btn" title="New group">+</button>
        </div>
        <div class="sidebar-list"></div>
        <div class="sidebar-footer">
          <div class="user-chip">
            <div class="user-avatar">${(state.user?.username?.[0] || "?").toUpperCase()}</div>
            <div>
              <div style="font-size:13px;font-weight:600">${state.user?.username || ""}</div>
              <a href="#/login" id="logout-link" style="font-size:11px;color:var(--color-text-muted)">Sign out</a>
            </div>
          </div>
        </div>
      </div>

      <div class="sidebar-threads">
        <div class="sidebar-header">
          <h2>Threads</h2>
          <button class="icon-btn" id="new-thread-btn" title="New thread">+</button>
        </div>
        <div class="sidebar-list"></div>
      </div>

      <div class="main-panel">
        <div class="empty-state" style="height:100%">
          <div class="empty-icon">💡</div>
          <p>Select a thread to start planning.<br/>Or create a new one in a group.</p>
        </div>
      </div>
    </div>
  `;

  document.getElementById("new-group-btn").addEventListener("click", () => {
    showCreateGroupModal(async (group) => {
      state.activeGroup = group;
      await renderGroupsSidebar();
      navigate(`/groups/${group.id}/threads`);
    });
  });

  document.getElementById("logout-link").addEventListener("click", (e) => {
    e.preventDefault();
    setToken(null);
    setUser(null);
    disconnectWs();
    navigate("/login");
  });

  document.getElementById("new-thread-btn").addEventListener("click", () => {
    if (!state.activeGroup) return;
    showCreateThreadModal(state.activeGroup.id, async (thread) => {
      state.activeThread = thread;
      await renderThreadSidebar(state.activeGroup.id);
      navigate(`/groups/${state.activeGroup.id}/threads/${thread.id}`);
    });
  });
}

// ── Auth guard ──────────────────────────────────────────────────────────────
async function requireAuth() {
  loadToken();
  if (!state.token) return false;
  if (!state.user) {
    try {
      const user = await api.me();
      setUser(user);
    } catch {
      setToken(null);
      return false;
    }
  }
  return true;
}

// ── Routes ──────────────────────────────────────────────────────────────────
route("/login", () => renderLogin());
route("/register", () => renderRegister());
route("/forgot-password", () => renderForgotPassword());
route("/reset-password", () => {
  const token = new URLSearchParams(location.search).get("token") ||
    location.hash.split("token=")[1];
  renderResetPassword(token);
});
route("/oauth-callback", async () => {
  const token = new URLSearchParams(location.search).get("token") ||
    location.hash.split("token=")[1];
  if (token) {
    setToken(token);
    try {
      const user = await api.me();
      setUser(user);
    } catch {}
  }
  navigate("/groups");
});

route("/groups", async () => {
  if (!(await requireAuth())) return navigate("/login");
  renderShell();
  await renderGroupsSidebar();
});

route("/groups/:groupId/threads", async ({ groupId }) => {
  if (!(await requireAuth())) return navigate("/login");
  renderShell();
  state.activeGroup = state.groups.find((g) => g.id === parseInt(groupId)) ||
    (await api.getGroup(groupId));
  await renderGroupsSidebar();
  await renderThreadSidebar(groupId);
});

route("/groups/:groupId/threads/:threadId", async ({ groupId, threadId }) => {
  if (!(await requireAuth())) return navigate("/login");
  renderShell();

  if (!state.groups.length) state.groups = await api.getGroups();
  state.activeGroup = state.groups.find((g) => g.id === parseInt(groupId)) || null;

  await renderGroupsSidebar();
  await renderThreadSidebar(groupId);

  state.activeThread = state.threads.find((t) => t.id === parseInt(threadId)) || null;
  await renderChat(groupId, threadId);
});

route("/groups/:groupId/threads/:threadId/docs", async ({ groupId, threadId }) => {
  if (!(await requireAuth())) return navigate("/login");
  renderShell();
  if (!state.groups.length) state.groups = await api.getGroups();
  state.activeGroup = state.groups.find((g) => g.id === parseInt(groupId)) || null;
  await renderGroupsSidebar();
  await renderThreadSidebar(groupId);
  await renderDocs(groupId, threadId);
});

route("/groups/:groupId/threads/:threadId/plan", async ({ groupId, threadId }) => {
  if (!(await requireAuth())) return navigate("/login");
  renderShell();

  if (!state.groups.length) state.groups = await api.getGroups();
  state.activeGroup = state.groups.find((g) => g.id === parseInt(groupId)) || null;

  await renderGroupsSidebar();
  await renderThreadSidebar(groupId);
  await renderPlan(groupId, threadId);
});

// Default: redirect based on auth
route("/", async () => {
  if (await requireAuth()) navigate("/groups");
  else navigate("/login");
});

initRouter();

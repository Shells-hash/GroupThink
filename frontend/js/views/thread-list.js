import { api } from "../api.js";
import { state } from "../state.js";
import { navigate } from "../router.js";
import { showInviteModal } from "./groups.js";

export async function renderThreadSidebar(groupId) {
  const sidebar = document.querySelector(".sidebar-threads");
  if (!sidebar) return;

  const group = state.groups.find((g) => g.id === parseInt(groupId)) || { name: "Group" };
  sidebar.querySelector(".sidebar-header h2").textContent = group.name;

  // Add invite button if not already there
  let inviteBtn = sidebar.querySelector("#invite-btn");
  if (!inviteBtn) {
    const header = sidebar.querySelector(".sidebar-header");
    inviteBtn = document.createElement("button");
    inviteBtn.id = "invite-btn";
    inviteBtn.className = "btn btn-ghost btn-sm";
    inviteBtn.title = "Invite someone";
    inviteBtn.textContent = "+ Invite";
    inviteBtn.style.fontSize = "12px";
    header.appendChild(inviteBtn);
  }
  inviteBtn.onclick = () => showInviteModal(parseInt(groupId));

  try {
    state.threads = await api.getThreads(groupId);
  } catch {
    state.threads = [];
  }

  const list = sidebar.querySelector(".sidebar-list");
  list.innerHTML = state.threads.length
    ? state.threads.map((t) => `
        <div class="sidebar-item ${state.activeThread?.id === t.id ? "active" : ""}"
             data-thread-id="${t.id}" data-group-id="${groupId}">
          <span style="font-size:14px">#</span>
          <span>${t.title}</span>
        </div>
      `).join("")
    : `<div class="empty-state"><p>No threads yet.<br/>Start a topic below.</p></div>`;

  list.querySelectorAll("[data-thread-id]").forEach((el) => {
    el.addEventListener("click", () => {
      navigate(`/groups/${el.dataset.groupId}/threads/${el.dataset.threadId}`);
    });
  });
}

export function showCreateThreadModal(groupId, onCreated) {
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal">
      <h3>New Thread</h3>
      <div class="form-group">
        <label>Topic title</label>
        <input class="input" id="thread-title" placeholder="e.g. Where should we eat?" />
      </div>
      <div id="thread-error" style="margin-top:8px;display:none"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button class="btn btn-primary" id="create-btn">Create</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  backdrop.querySelector("#cancel-btn").addEventListener("click", () => backdrop.remove());
  backdrop.querySelector("#create-btn").addEventListener("click", async () => {
    const title = backdrop.querySelector("#thread-title").value.trim();
    if (!title) return;
    try {
      const thread = await api.createThread(groupId, { title });
      backdrop.remove();
      onCreated(thread);
    } catch (e) {
      const err = backdrop.querySelector("#thread-error");
      err.className = "error-msg";
      err.style.display = "block";
      err.textContent = e.message;
    }
  });

  backdrop.querySelector("#thread-title").focus();
}

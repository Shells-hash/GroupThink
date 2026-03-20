import { api } from "../api.js";
import { state } from "../state.js";
import { navigate } from "../router.js";

export async function renderGroupsSidebar() {
  const sidebar = document.querySelector(".sidebar-groups");
  if (!sidebar) return;

  try {
    state.groups = await api.getGroups();
  } catch {
    state.groups = [];
  }

  const list = sidebar.querySelector(".sidebar-list");
  list.innerHTML = state.groups.length
    ? state.groups.map((g) => `
        <div class="sidebar-item ${state.activeGroup?.id === g.id ? "active" : ""}"
             data-group-id="${g.id}">
          <div class="item-avatar">${g.name[0].toUpperCase()}</div>
          <span>${g.name}</span>
        </div>
      `).join("")
    : `<div class="empty-state"><p>No groups yet.<br/>Create one below.</p></div>`;

  list.querySelectorAll("[data-group-id]").forEach((el) => {
    el.addEventListener("click", () => {
      navigate(`/groups/${el.dataset.groupId}/threads`);
    });
  });
}

export function showCreateGroupModal(onCreated) {
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal">
      <h3>New Group</h3>
      <div class="form-group">
        <label>Group name</label>
        <input class="input" id="group-name" placeholder="e.g. Weekend Trip Planning" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label>Description (optional)</label>
        <input class="input" id="group-desc" placeholder="What is this group for?" />
      </div>
      <div id="modal-error" style="margin-top:8px;display:none"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button class="btn btn-primary" id="create-btn">Create</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  backdrop.querySelector("#cancel-btn").addEventListener("click", () => backdrop.remove());
  backdrop.querySelector("#create-btn").addEventListener("click", async () => {
    const name = backdrop.querySelector("#group-name").value.trim();
    if (!name) return;
    try {
      const group = await api.createGroup({
        name,
        description: backdrop.querySelector("#group-desc").value.trim() || null,
      });
      backdrop.remove();
      onCreated(group);
    } catch (e) {
      const err = backdrop.querySelector("#modal-error");
      err.className = "error-msg";
      err.style.display = "block";
      err.textContent = e.message;
    }
  });

  backdrop.querySelector("#group-name").focus();
}

export function showInviteModal(groupId) {
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal">
      <h3>Invite Friend</h3>
      <div class="form-group">
        <label>Username</label>
        <input class="input" id="invite-username" placeholder="Enter their username" />
      </div>
      <div id="invite-error" style="margin-top:8px;display:none"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button class="btn btn-primary" id="invite-btn">Invite</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  backdrop.querySelector("#cancel-btn").addEventListener("click", () => backdrop.remove());
  backdrop.querySelector("#invite-btn").addEventListener("click", async () => {
    const username = backdrop.querySelector("#invite-username").value.trim();
    if (!username) return;
    try {
      await api.inviteMember(groupId, { username });
      backdrop.remove();
    } catch (e) {
      const err = backdrop.querySelector("#invite-error");
      err.className = "error-msg";
      err.style.display = "block";
      err.textContent = e.message;
    }
  });

  backdrop.querySelector("#invite-username").focus();
}

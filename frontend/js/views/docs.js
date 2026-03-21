import { api } from "../api.js";
import { state } from "../state.js";
import { navigate } from "../router.js";
import { renderMarkdown, initDiagrams } from "../markdown.js";

export async function renderDocs(groupId, threadId) {
  const thread = state.threads.find((t) => t.id === parseInt(threadId));
  const main = document.querySelector(".main-panel");
  if (!main) return;

  main.innerHTML = `
    <div class="chat-header">
      <h3>${thread ? "# " + _esc(thread.title) + " — Docs" : "Docs"}</h3>
      <div class="header-actions">
        <button class="btn btn-ghost btn-sm" id="back-to-chat-btn">← Chat</button>
        <button class="btn btn-primary btn-sm" id="new-doc-btn">+ New Doc</button>
      </div>
    </div>
    <div class="docs-layout">
      <div class="docs-sidebar">
        <div class="docs-sidebar-list" id="docs-list">
          <div class="empty-state" style="height:200px"><p>Loading…</p></div>
        </div>
      </div>
      <div class="docs-main" id="docs-main">
        <div class="empty-state" style="height:100%">
          <div class="empty-icon">📄</div>
          <p>Select a document or create a new one.</p>
        </div>
      </div>
    </div>
  `;

  document.getElementById("back-to-chat-btn").addEventListener("click", () => {
    navigate(`/groups/${groupId}/threads/${threadId}`);
  });

  document.getElementById("new-doc-btn").addEventListener("click", () => {
    _showNewDocModal(groupId, threadId);
  });

  await _loadDocs(threadId);
}

async function _loadDocs(threadId, selectId = null) {
  const list = document.getElementById("docs-list");
  if (!list) return;
  try {
    const docs = await api.getDocs(threadId);
    if (!docs.length) {
      list.innerHTML = `<div class="empty-state" style="padding:32px 16px;text-align:center">
        <div class="empty-icon">📄</div>
        <p style="font-size:13px;margin-top:8px">No documents yet.<br/>Create one to start planning.</p>
      </div>`;
      return;
    }
    list.innerHTML = docs.map((d) => `
      <div class="docs-sidebar-item${d.id === selectId ? " active" : ""}" data-id="${d.id}">
        <div class="docs-item-title">${_esc(d.title)}</div>
        <div class="docs-item-meta">${_esc(d.author_username || "AI")} · ${_fmtDate(d.updated_at)}</div>
      </div>
    `).join("");

    list.querySelectorAll(".docs-sidebar-item").forEach((el) => {
      el.addEventListener("click", () => {
        list.querySelectorAll(".docs-sidebar-item").forEach((e) => e.classList.remove("active"));
        el.classList.add("active");
        const doc = docs.find((d) => d.id === parseInt(el.dataset.id));
        if (doc) _renderDocEditor(doc, threadId);
      });
    });

    const toSelect = selectId ? list.querySelector(`[data-id="${selectId}"]`) : list.querySelector(".docs-sidebar-item");
    if (toSelect) toSelect.click();
  } catch {
    list.innerHTML = `<div class="empty-state"><p>Error loading documents.</p></div>`;
  }
}

function _renderDocEditor(doc, threadId) {
  const main = document.getElementById("docs-main");
  if (!main) return;

  main.innerHTML = `
    <div class="doc-editor">
      <div class="doc-editor-header">
        <input class="doc-title-input" id="doc-title" value="${_esc(doc.title)}" placeholder="Document title" />
        <div class="doc-header-actions">
          <button class="btn btn-ghost btn-sm" id="doc-preview-btn">Preview</button>
          <button class="btn btn-ghost btn-sm" id="doc-edit-btn" style="display:none">Edit</button>
          <button class="btn btn-ghost btn-sm" id="doc-ai-btn">AI Draft</button>
          <button class="btn btn-primary btn-sm" id="doc-save-btn">Save</button>
          <button class="btn btn-danger btn-sm" id="doc-delete-btn">Delete</button>
        </div>
      </div>
      <div class="doc-editor-body">
        <textarea class="doc-textarea" id="doc-content" placeholder="Write in Markdown…\n\nCreate diagrams with mermaid code blocks:\n\`\`\`mermaid\nflowchart TD\n  A[Start] --> B[Step]\n\`\`\`">${_esc(doc.content)}</textarea>
        <div class="doc-preview markdown-body" id="doc-preview" style="display:none"></div>
      </div>
    </div>
  `;

  document.getElementById("doc-preview-btn").addEventListener("click", () => {
    const content = document.getElementById("doc-content").value;
    const preview = document.getElementById("doc-preview");
    preview.innerHTML = renderMarkdown(content);
    preview.style.display = "block";
    document.getElementById("doc-content").style.display = "none";
    document.getElementById("doc-preview-btn").style.display = "none";
    document.getElementById("doc-edit-btn").style.display = "";
    initDiagrams(preview);
  });

  document.getElementById("doc-edit-btn").addEventListener("click", () => {
    document.getElementById("doc-preview").style.display = "none";
    document.getElementById("doc-content").style.display = "";
    document.getElementById("doc-preview-btn").style.display = "";
    document.getElementById("doc-edit-btn").style.display = "none";
  });

  document.getElementById("doc-save-btn").addEventListener("click", async () => {
    const btn = document.getElementById("doc-save-btn");
    btn.disabled = true; btn.textContent = "Saving…";
    try {
      const updated = await api.updateDoc(doc.id, {
        title: document.getElementById("doc-title").value,
        content: document.getElementById("doc-content").value,
      });
      doc.title = updated.title;
      doc.content = updated.content;
      btn.textContent = "Saved!";
      setTimeout(() => { btn.disabled = false; btn.textContent = "Save"; }, 1500);
      await _loadDocs(threadId, doc.id);
    } catch {
      btn.disabled = false; btn.textContent = "Save";
    }
  });

  document.getElementById("doc-ai-btn").addEventListener("click", async () => {
    const btn = document.getElementById("doc-ai-btn");
    btn.disabled = true; btn.textContent = "Drafting…";
    try {
      const updated = await api.aiDraftDoc(doc.id);
      document.getElementById("doc-content").value = updated.content;
      doc.content = updated.content;
      // If currently in preview mode, refresh it
      const preview = document.getElementById("doc-preview");
      if (preview.style.display !== "none") {
        preview.innerHTML = renderMarkdown(updated.content);
        initDiagrams(preview);
      }
    } catch (e) {
      alert("AI draft failed: " + e.message);
    } finally {
      btn.disabled = false; btn.textContent = "AI Draft";
    }
  });

  document.getElementById("doc-delete-btn").addEventListener("click", async () => {
    if (!confirm(`Delete "${doc.title}"?`)) return;
    try {
      await api.deleteDoc(doc.id);
      const main = document.getElementById("docs-main");
      if (main) main.innerHTML = `<div class="empty-state" style="height:100%"><div class="empty-icon">📄</div><p>Document deleted.</p></div>`;
      await _loadDocs(threadId);
    } catch (e) {
      alert("Delete failed: " + e.message);
    }
  });
}

function _showNewDocModal(groupId, threadId) {
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal">
      <h3>New Document</h3>
      <div class="form-group">
        <label>Title</label>
        <input class="input" id="ndoc-title" placeholder="e.g. Project Plan, Timeline, Meeting Notes…" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label>Instructions for AI (optional)</label>
        <textarea class="input" id="ndoc-instructions" rows="2" placeholder="e.g. Create a project timeline with milestones and a Gantt chart…" style="resize:vertical"></textarea>
      </div>
      <div style="margin-top:12px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="ndoc-ai" style="accent-color:var(--color-primary);width:16px;height:16px" />
        <label for="ndoc-ai" style="font-size:13px;cursor:pointer">Let AI draft this document from our discussion</label>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="ndoc-cancel">Cancel</button>
        <button class="btn btn-primary" id="ndoc-create">Create</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  backdrop.querySelector("#ndoc-cancel").addEventListener("click", () => backdrop.remove());
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) backdrop.remove(); });
  backdrop.querySelector("#ndoc-title").focus();

  backdrop.querySelector("#ndoc-create").addEventListener("click", async () => {
    const btn = backdrop.querySelector("#ndoc-create");
    const title = backdrop.querySelector("#ndoc-title").value.trim();
    if (!title) { backdrop.querySelector("#ndoc-title").focus(); return; }
    const instructions = backdrop.querySelector("#ndoc-instructions").value.trim();
    const aiGenerate = backdrop.querySelector("#ndoc-ai").checked;
    btn.disabled = true;
    btn.textContent = aiGenerate ? "Drafting…" : "Creating…";
    try {
      const doc = aiGenerate
        ? await api.generateDoc(threadId, { title, instructions })
        : await api.createDoc(threadId, { title, content: "" });
      backdrop.remove();
      await _loadDocs(threadId, doc.id);
    } catch (e) {
      btn.disabled = false; btn.textContent = "Create";
      alert("Error: " + e.message);
    }
  });
}

function _esc(str) {
  return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function _fmtDate(d) {
  return new Date(d).toLocaleDateString([], { month: "short", day: "numeric" });
}

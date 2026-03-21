// Markdown + Mermaid rendering utility
// Requires window.marked (marked.js) and window.mermaid (mermaid.js) loaded as globals

export function renderMarkdown(text) {
  if (!text) return "";
  if (!window.marked) return _escapeHtml(text);
  return window.marked.parse(text);
}

export async function initDiagrams(container) {
  if (!window.mermaid || !container) return;
  const blocks = container.querySelectorAll("code.language-mermaid");
  for (const block of blocks) {
    const pre = block.parentElement;
    const code = block.textContent.trim();
    const id = "mermaid-" + Math.random().toString(36).slice(2, 9);
    try {
      const { svg } = await window.mermaid.render(id, code);
      const wrapper = document.createElement("div");
      wrapper.className = "mermaid-diagram";
      wrapper.innerHTML = svg;
      pre.replaceWith(wrapper);
    } catch {
      const wrapper = document.createElement("div");
      wrapper.className = "mermaid-error";
      wrapper.textContent = "Diagram could not be rendered";
      pre.replaceWith(wrapper);
    }
  }
}

function _escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

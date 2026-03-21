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

export function enhanceCodeBlocks(container) {
  if (!container) return;
  container.querySelectorAll("pre code").forEach((block) => {
    // Skip mermaid blocks (already handled by initDiagrams)
    if (block.classList.contains("language-mermaid")) return;
    // Skip if already enhanced
    if (block.parentElement.classList.contains("code-block-wrapper")) return;

    // Syntax highlight
    if (window.hljs) {
      window.hljs.highlightElement(block);
    }

    // Wrap in a container with copy button
    const pre = block.parentElement;
    const lang = (block.className.match(/language-(\w+)/) || [])[1] || "";
    const wrapper = document.createElement("div");
    wrapper.className = "code-block-wrapper";
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const toolbar = document.createElement("div");
    toolbar.className = "code-block-toolbar";
    toolbar.innerHTML = `
      ${lang ? `<span class="code-lang">${lang}</span>` : ""}
      <button class="copy-code-btn" title="Copy code">Copy</button>
    `;
    wrapper.insertBefore(toolbar, pre);

    toolbar.querySelector(".copy-code-btn").addEventListener("click", () => {
      const btn = toolbar.querySelector(".copy-code-btn");
      navigator.clipboard.writeText(block.innerText).then(() => {
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = "Copy"; }, 2000);
      });
    });
  });
}

function _escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

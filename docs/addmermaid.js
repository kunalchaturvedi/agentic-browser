(() => {
  const ensureMermaid = async () => {
    if (window.mermaid) {
      return window.mermaid;
    }

    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js";
    script.async = true;

    await new Promise((resolve, reject) => {
      script.addEventListener("load", resolve, { once: true });
      script.addEventListener("error", reject, { once: true });
      document.head.appendChild(script);
    });

    return window.mermaid;
  };

  const renderMermaidBlocks = async () => {
    const blocks = Array.from(document.querySelectorAll("pre code.language-mermaid"));
    if (!blocks.length) {
      return;
    }

    const mermaid = await ensureMermaid();
    mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

    for (const [index, block] of blocks.entries()) {
      const container = document.createElement("div");
      container.className = "mermaid";
      container.textContent = block.textContent ?? "";

      const pre = block.closest("pre");
      if (!pre) {
        continue;
      }

      pre.replaceWith(container);
      await mermaid.run({ nodes: [container] });
      container.dataset.mermaidId = `diagram-${index + 1}`;
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      void renderMermaidBlocks();
    });
  } else {
    void renderMermaidBlocks();
  }
})();

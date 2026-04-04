document.addEventListener("DOMContentLoaded", () => {
  bindQrPreview();

  const modal = document.querySelector("[data-modal-root]");
  if (!modal) {
    bindSectionLinks();
    return;
  }

  const closeUrl = new URL(window.location.href);
  closeUrl.searchParams.delete("detail");
  const modalPanel = modal.querySelector("[data-modal-panel]");

  // Keep the detail view open unless the user explicitly closes it.
  modalPanel?.addEventListener("click", (event) => {
    event.stopPropagation();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (closeQrPreview()) {
        return;
      }
      window.location.href = closeUrl.toString();
    }
  });

  bindSectionLinks(modal);
});

function bindQrPreview() {
  const previewRoot = document.querySelector("[data-qr-preview-root]");
  const triggers = document.querySelectorAll("[data-qr-trigger]");
  if (!previewRoot || !triggers.length) {
    return;
  }

  const previewImage = previewRoot.querySelector("[data-qr-preview-image]");
  const previewTitle = previewRoot.querySelector("[data-qr-preview-title]");
  const previewSubtitle = previewRoot.querySelector("[data-qr-preview-subtitle]");
  const closeButtons = previewRoot.querySelectorAll("[data-qr-close]");

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const src = trigger.getAttribute("data-qr-src");
      if (!src || !previewImage) {
        return;
      }

      const title = trigger.getAttribute("data-qr-title") || "";
      const subtitle = trigger.getAttribute("data-qr-subtitle") || "";

      previewImage.src = src;
      previewImage.alt = title || "二维码预览";
      if (previewTitle) {
        previewTitle.textContent = title;
      }
      if (previewSubtitle) {
        previewSubtitle.textContent = subtitle;
      }

      previewRoot.classList.remove("hidden");
      previewRoot.classList.add("flex");
      previewRoot.setAttribute("aria-hidden", "false");
      if (!document.querySelector("[data-modal-root]")) {
        document.body.classList.add("overflow-hidden");
      }
    });
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      closeQrPreview();
    });
  });
}

function closeQrPreview() {
  const previewRoot = document.querySelector("[data-qr-preview-root]");
  if (!previewRoot || previewRoot.classList.contains("hidden")) {
    return false;
  }

  const previewImage = previewRoot.querySelector("[data-qr-preview-image]");
  if (previewImage) {
    previewImage.removeAttribute("src");
    previewImage.removeAttribute("alt");
  }

  previewRoot.classList.add("hidden");
  previewRoot.classList.remove("flex");
  previewRoot.setAttribute("aria-hidden", "true");
  if (!document.querySelector("[data-modal-root]")) {
    document.body.classList.remove("overflow-hidden");
  }
  return true;
}

function bindSectionLinks(scope = document) {
  const links = scope.querySelectorAll("[data-section-link]");
  if (!links.length) {
    return;
  }

  links.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const targetId = link.getAttribute("data-section-link");
      if (!targetId) {
        return;
      }

      const root = link.closest("[data-modal-root]") || document;
      const scrollContainer = root.querySelector("[data-detail-scroll]");
      const target = root.querySelector(`#${CSS.escape(targetId)}`);

      if (!target) {
        return;
      }

      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });

      if (scrollContainer) {
        scrollContainer.focus?.();
      }
    });
  });
}

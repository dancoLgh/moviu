document.documentElement.classList.add("enhanced");

const header = document.querySelector("[data-header]");
const menuButton = document.querySelector("[data-menu-button]");
const menu = document.querySelector("[data-menu]");
const copyButton = document.querySelector("[data-copy-code]");
const codeBlock = document.querySelector("[data-code]");
const downloadModal = document.querySelector("[data-download-modal]");
const downloadDialog = downloadModal?.querySelector("[role='dialog']");
const downloadCountdown = downloadModal?.querySelector("[data-download-countdown]");
const downloadPlatform = downloadModal?.querySelector("[data-download-platform]");
const downloadProgress = downloadModal?.querySelector("[data-download-progress]");
const directDownload = downloadModal?.querySelector("[data-download-direct]");
const dlocalStatus = downloadModal?.querySelector("[data-dlocal-status]");

const DLOCAL_GO_SCRIPT = "https://static.dlocalgo.com/dlocalgo.min.js";
const DLOCAL_GO_CHECKOUT_ID = "DKGuMAOMKKGaGHsreDzGCdYmGjNMCJKs";
const initializedDonationAmounts = new Set();
const downloadScheduler = window.MoviuDownload.createDownloadScheduler();
let dlocalGoPromise;
let activeDownloadJob;
let lastManualDownloadAt = 0;
let previousFocus;
let modalBackgroundState = [];

function updateHeader() {
  header?.classList.toggle("scrolled", window.scrollY > 12);
}

function closeMenu() {
  menu?.classList.remove("open");
  menuButton?.setAttribute("aria-expanded", "false");
}

menuButton?.addEventListener("click", () => {
  const isOpen = menu?.classList.toggle("open") ?? false;
  menuButton.setAttribute("aria-expanded", String(isOpen));
});

menu?.addEventListener("click", (event) => {
  if (event.target.closest("a")) {
    closeMenu();
  }
});

window.addEventListener("scroll", updateHeader, { passive: true });
updateHeader();

document.querySelectorAll("[data-year]").forEach((element) => {
  element.textContent = String(new Date().getFullYear());
});

copyButton?.addEventListener("click", async () => {
  if (!codeBlock || !navigator.clipboard) {
    return;
  }
  await navigator.clipboard.writeText(codeBlock.textContent.trim());
  copyButton.textContent = "Copiado";
  window.setTimeout(() => {
    copyButton.textContent = "Copiar";
  }, 1600);
});

function loadDlocalGo() {
  if (window.DlocalGo) {
    return Promise.resolve(window.DlocalGo);
  }
  if (dlocalGoPromise) {
    return dlocalGoPromise;
  }

  dlocalGoPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector(`script[src="${DLOCAL_GO_SCRIPT}"]`);
    const script = existingScript || document.createElement("script");
    const timeout = window.setTimeout(
      () => handleFailure(new Error("dLocal Go tardó demasiado en responder")),
      10000
    );
    const cleanup = () => {
      window.clearTimeout(timeout);
      script.removeEventListener("load", handleLoad);
      script.removeEventListener("error", handleError);
    };
    const handleLoad = () => {
      if (window.DlocalGo) {
        cleanup();
        resolve(window.DlocalGo);
      } else {
        handleFailure(new Error("dLocal Go no quedó disponible"));
      }
    };
    const handleError = () => handleFailure(new Error("No se pudo cargar dLocal Go"));
    function handleFailure(error) {
      cleanup();
      script.remove();
      dlocalGoPromise = undefined;
      reject(error);
    }

    script.addEventListener("load", handleLoad, { once: true });
    script.addEventListener("error", handleError, { once: true });
    if (!existingScript) {
      script.src = DLOCAL_GO_SCRIPT;
      script.async = true;
      document.body.appendChild(script);
    }
  });
  return dlocalGoPromise;
}

async function showDonationAmount(amount) {
  document.querySelectorAll("[data-donation-amount]").forEach((button) => {
    const selected = button.dataset.donationAmount === amount;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  document.querySelectorAll("[data-dlocal-amount]").forEach((checkout) => {
    checkout.hidden = checkout.dataset.dlocalAmount !== amount;
  });

  const checkout = document.querySelector(`[data-dlocal-amount="${amount}"]`);
  if (!checkout || initializedDonationAmounts.has(amount)) {
    if (dlocalStatus) dlocalStatus.hidden = true;
    return;
  }

  if (dlocalStatus) {
    dlocalStatus.hidden = false;
    dlocalStatus.textContent = "Cargando pago seguro...";
  }
  try {
    const DlocalGo = await loadDlocalGo();
    const numericAmount = window.MoviuDownload.normalizeDonationAmount(amount);
    new DlocalGo(DLOCAL_GO_CHECKOUT_ID).createCheckout(checkout.id, {
      subType: "BUTTON",
      country: "",
      currency: "USD",
      amount: numericAmount,
      lang: "",
      text: "Donar con dLocal Go",
    });
    initializedDonationAmounts.add(amount);
    if (dlocalStatus) dlocalStatus.hidden = true;
  } catch (error) {
    console.error(error);
    if (dlocalStatus) {
      dlocalStatus.hidden = false;
      dlocalStatus.textContent = "No se pudo cargar el pago. La descarga continuará normalmente.";
    }
  }
}

function triggerDownload(url) {
  const link = document.createElement("a");
  link.href = url;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function openDownloadModal(link) {
  if (!downloadModal) return;
  previousFocus = document.activeElement;

  if (downloadPlatform) downloadPlatform.textContent = link.dataset.platform || "tu plataforma";
  if (downloadCountdown) downloadCountdown.textContent = "3";
  if (directDownload) {
    directDownload.href = link.href;
    directDownload.textContent = "¿La descarga no comenzó? Descargar ahora";
  }
  downloadModal.hidden = false;
  document.body.classList.add("modal-open");
  setModalBackgroundInert(true);
  downloadDialog?.querySelector("[data-download-close]")?.focus();

  if (downloadProgress) {
    downloadProgress.classList.remove("running");
    void downloadProgress.offsetWidth;
    downloadProgress.classList.add("running");
  }

  let job;
  job = downloadScheduler.schedule(link.href, {
    onTick(seconds) {
      if (activeDownloadJob !== job) return;
      if (downloadCountdown) downloadCountdown.textContent = String(seconds);
      if (seconds === 0 && directDownload) directDownload.textContent = "Descargar nuevamente";
    },
    onStart: triggerDownload,
  });
  activeDownloadJob = job;
  showDonationAmount("10");
}

function closeDownloadModal() {
  if (!downloadModal) return;
  downloadModal.hidden = true;
  document.body.classList.remove("modal-open");
  setModalBackgroundInert(false);
  previousFocus?.focus();
}

function setModalBackgroundInert(inert) {
  const background = document.querySelectorAll("body > header, body > main, body > footer");
  if (inert) {
    modalBackgroundState = Array.from(background, (element) => ({
      element,
      ariaHidden: element.getAttribute("aria-hidden"),
      inert: element.inert,
    }));
    modalBackgroundState.forEach(({ element }) => {
      element.inert = true;
      element.setAttribute("aria-hidden", "true");
    });
    return;
  }

  modalBackgroundState.forEach(({ element, ariaHidden, inert: previousInert }) => {
    element.inert = previousInert;
    if (ariaHidden === null) element.removeAttribute("aria-hidden");
    else element.setAttribute("aria-hidden", ariaHidden);
  });
  modalBackgroundState = [];
}

function trapDialogFocus(event) {
  if (event.key !== "Tab" || !downloadDialog) return;
  const focusable = Array.from(
    downloadDialog.querySelectorAll(
      'a[href], button:not([disabled]), iframe, input:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => !element.hidden && element.getClientRects().length > 0);
  if (!focusable.length) return;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

document.querySelectorAll("[data-download]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    openDownloadModal(link);
  });
});

document.querySelectorAll("[data-download-close]").forEach((button) => {
  button.addEventListener("click", closeDownloadModal);
});

document.querySelectorAll("[data-donation-amount]").forEach((button) => {
  button.addEventListener("click", () => showDonationAmount(button.dataset.donationAmount));
});

directDownload?.addEventListener("click", (event) => {
  event.preventDefault();
  if (!activeDownloadJob) return;
  const now = Date.now();
  if (now - lastManualDownloadAt < 1500) return;
  lastManualDownloadAt = now;
  if (!activeDownloadJob.started) {
    activeDownloadJob.startNow();
    return;
  }
  triggerDownload(activeDownloadJob.url);
});

document.addEventListener("keydown", (event) => {
  if (downloadModal && !downloadModal.hidden) trapDialogFocus(event);
  if (event.key === "Escape" && downloadModal && !downloadModal.hidden) {
    closeDownloadModal();
  }
});

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const revealElements = document.querySelectorAll(".reveal");

if (reduceMotion || !("IntersectionObserver" in window)) {
  revealElements.forEach((element) => element.classList.add("visible"));
} else {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  revealElements.forEach((element) => observer.observe(element));
}

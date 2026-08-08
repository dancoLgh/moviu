document.documentElement.classList.add("enhanced");

const header = document.querySelector("[data-header]");
const menuButton = document.querySelector("[data-menu-button]");
const menu = document.querySelector("[data-menu]");
const copyButton = document.querySelector("[data-copy-code]");
const codeBlock = document.querySelector("[data-code]");

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

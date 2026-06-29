/* =============================================================================
   Backcast Showcase — interactions (vanilla, dependency-free)
   Pairs with markup in index.html and components in css/styles.css.
   ========================================================================== */
(() => {
  "use strict";

  /* --- Reveal on scroll (progressive enhancement; no-op if unsupported) --- */
  const revealEls = document.querySelectorAll("[data-reveal]");
  if (revealEls.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -10% 0px" }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-visible"));
  }

  /* --- Mobile navigation toggle --- */
  const navToggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-nav]");
  if (navToggle && nav) {
    const setOpen = (open) => {
      nav.classList.toggle("is-open", open);
      navToggle.setAttribute("aria-expanded", String(open));
    };
    navToggle.addEventListener("click", () =>
      setOpen(!nav.classList.contains("is-open"))
    );
    // Close the panel after following a link (mobile)
    nav.querySelectorAll("a").forEach((a) =>
      a.addEventListener("click", () => setOpen(false))
    );
  }

  /* --- FAQ accordion (ready for when FAQ sections are added) --- */
  document.querySelectorAll("[data-accordion-trigger]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = btn.closest("[data-accordion]");
      const panel = item ? item.querySelector("[data-accordion-panel]") : null;
      const open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      if (item) item.classList.toggle("is-open", !open);
      if (panel) panel.hidden = open;
    });
  });

  /* --- Footer year --- */
  document.querySelectorAll("[data-year]").forEach((el) => {
    el.textContent = String(new Date().getFullYear());
  });
})();

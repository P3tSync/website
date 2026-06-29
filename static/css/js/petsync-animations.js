(function () {
  const animeApi = window.anime;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const themeToggle = document.querySelector(".theme-toggle");
  const root = document.documentElement;

  function setTheme(theme) {
    const isDark = theme === "dark";
    root.classList.toggle("dark", isDark);
    if (themeToggle) {
      themeToggle.textContent = isDark ? "☀️" : "🌙";
      themeToggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
      themeToggle.setAttribute("aria-pressed", isDark);
    }
    localStorage.setItem("petsync-theme", theme);
  }

  function getStoredTheme() {
    const stored = localStorage.getItem("petsync-theme");
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      setTheme(root.classList.contains("dark") ? "light" : "dark");
    });
  }

  setTheme(getStoredTheme());

  if (!animeApi || prefersReducedMotion) {
    document.documentElement.classList.add("motion-ready");
    return;
  }

  const easeOut = "easeOutCubic";
  const spring = "easeOutBack";

  function run(targets, params) {
    if (!document.querySelector(targets)) return;
    animeApi({ targets, ...params });
  }

  document.documentElement.classList.add("motion-ready");

  run(".site-nav", {
    translateY: [-18, 0],
    opacity: [0, 1],
    duration: 520,
    easing: easeOut
  });

  run(".page-head, .hero-copy", {
    translateY: [18, 0],
    opacity: [0, 1],
    duration: 650,
    delay: 80,
    easing: easeOut
  });

  run(".kitchen-tile, .clinic-card, .profile-card, .history-row, .cart-line", {
    translateY: [18, 0],
    opacity: [0, 1],
    duration: 560,
    delay: animeApi.stagger ? animeApi.stagger(55, { start: 120 }) : 120,
    easing: easeOut
  });

  run(".filter-form .field-row", {
    translateY: [10, 0],
    opacity: [0, 1],
    duration: 420,
    delay: animeApi.stagger ? animeApi.stagger(45, { start: 140 }) : 140,
    easing: easeOut
  });

  run(".dial-wrap svg", {
    scale: [0.96, 1],
    rotate: [-2, 0],
    opacity: [0, 1],
    duration: 900,
    delay: 220,
    easing: easeOut
  });

  if (animeApi.timeline && document.querySelector(".clockwork-dial")) {
    animeApi.timeline({ loop: true, easing: "easeInOutSine" })
      .add({
        targets: ".tick",
        translateY: [-2, 0],
        opacity: [0.35, 1],
        duration: 500,
        delay: animeApi.stagger ? animeApi.stagger(6) : 0
      })
      .add({
        targets: ".ticker",
        rotate: 360,
        duration: 2400,
        easing: "linear"
      }, 0);
  }

  run(".confirm-icon", {
    scale: [0.55, 1],
    opacity: [0, 1],
    duration: 720,
    easing: spring
  });

  document.querySelectorAll(".btn, .slot-chip, .qty-btn, .kitchen-tile, .clinic-card").forEach((el) => {
    el.addEventListener("mouseenter", () => {
      animeApi({ targets: el, scale: 1.018, duration: 180, easing: easeOut });
    });
    el.addEventListener("mouseleave", () => {
      animeApi({ targets: el, scale: 1, duration: 220, easing: easeOut });
    });
  });
})();

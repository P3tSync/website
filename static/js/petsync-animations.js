/* Petsync motion — vanilla motion-ui adaptation: transform/opacity only, reduced-motion safe */
(function () {
  var prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.documentElement.classList.add("motion-ready");

  if (prefersReduced) return;

  var lowEnd = (navigator.deviceMemory !== undefined && navigator.deviceMemory <= 2) ||
    (navigator.deviceMemory === undefined && navigator.hardwareConcurrency <= 4);
  if (lowEnd) document.documentElement.style.setProperty("--motion-scale", "0.6");

  var revealEls = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window) || !revealEls.length) {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry, i) {
      if (entry.isIntersecting) {
        entry.target.style.transitionDelay = Math.min(i * 80, 240) + "ms";
        entry.target.classList.add("is-visible");
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  revealEls.forEach(function (el) { io.observe(el); });

  /* CozyPaws letter stagger: each letter starts 30ms after the previous */
  document.querySelectorAll(".cozy-word").forEach(function (word) {
    word.querySelectorAll(".cozy-letter").forEach(function (letter, i) {
      letter.style.setProperty("--i", i);
    });
  });
})();

/* ==========================================================================
   WARHAMMER 40,000 — Vitrine statique
   nav.js : menu burger (mobile), surlignage du lien actif, filigrane aquila.
   JavaScript vanilla, aucune dépendance. Fonctionne en file:// (double-clic).
   ========================================================================== */
(function () {
  "use strict";

  /* ---- 1) Menu burger : bascule l'affichage de la liste de liens ---- */
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.setAttribute("aria-expanded", "false");
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Fermer le menu" : "Ouvrir le menu");
    });
    // Ferme le menu après un clic sur un lien (utile sur mobile)
    links.addEventListener("click", function (e) {
      if (e.target && e.target.tagName === "A") {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---- 2) Lien actif : met en évidence la page courante ---- */
  var current = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  var anchorList = document.querySelectorAll(".nav-links a");
  anchorList.forEach(function (a) {
    var href = (a.getAttribute("href") || "").toLowerCase();
    var file = href.split("/").pop();
    if (!file) file = "index.html";
    if (file === current) {
      a.classList.add("active");
      a.setAttribute("aria-current", "page");
    }
  });

  /* ---- 3) Filigrane aquila (aigle impérial à deux têtes), SVG inline ---- */
  var host = document.querySelector(".aquila-bg");
  if (host) {
    host.innerHTML =
      '<svg viewBox="0 0 200 200" width="100%" height="100%" ' +
      'fill="currentColor" aria-hidden="true" focusable="false">' +
      '<g stroke="currentColor" stroke-width="2.5" fill="none">' +
      // Corps central
      '<line x1="100" y1="55" x2="100" y2="150"/>' +
      // Tête droite
      '<path d="M100 60 C112 50 128 50 138 40 C130 54 124 60 120 66"/>' +
      // Tête gauche
      '<path d="M100 60 C88 50 72 50 62 40 C70 54 76 60 80 66"/>' +
      // Aile droite (plumes)
      '<path d="M100 78 C130 70 165 78 190 60"/>' +
      '<path d="M100 92 C132 86 168 96 192 82"/>' +
      '<path d="M100 106 C130 104 162 116 184 108"/>' +
      '<path d="M100 120 C126 122 150 136 170 134"/>' +
      // Aile gauche (plumes)
      '<path d="M100 78 C70 70 35 78 10 60"/>' +
      '<path d="M100 92 C68 86 32 96 8 82"/>' +
      '<path d="M100 106 C70 104 38 116 16 108"/>' +
      '<path d="M100 120 C74 122 50 136 30 134"/>' +
      // Queue / socle
      '<path d="M100 150 C94 162 90 172 88 184"/>' +
      '<path d="M100 150 C106 162 110 172 112 184"/>' +
      '</g>' +
      // Écu central
      '<circle cx="100" cy="108" r="9" fill="currentColor" opacity="0.6"/>' +
      '</svg>';
  }
})();

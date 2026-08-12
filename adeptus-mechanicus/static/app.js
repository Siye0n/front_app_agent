/* =========================================================
   Adeptus Mechanicus — canal de communication (chat bilatéral temps réel)
   - Rend les bulles visiteur (droite) / Magos (gauche + aquila)
   - Fade-in à l'apparition, typing indicator après envoi visiteur
   - Typing effect progressif pour les messages du Magos
   - TEMPS RÉEL : SocketIO pousse 'historique' (au connect) et
     'nouvelle_reponse' (dès qu'une réponse Magos est écrite).
     Plus de polling périodique.
   ========================================================= */

(function () {
  "use strict";

  var TYPING_INDICATOR_MS = 1200; // durée simulation frappe Magos

  var chatLog = document.getElementById("chat-log");
  var form = document.getElementById("contact-form");
  var nomInput = document.getElementById("nom");
  var msgInput = document.getElementById("message");
  var transmitBtn = document.getElementById("transmit-btn");
  var typingIndicator = document.getElementById("typing-indicator");
  var lastSyncEl = document.getElementById("last-sync");

  // IDs déjà affichés (pour ne pas re-rendre / rejouer les animations)
  var renderedIds = new Set();
  // Booléen : une réponse Magos vient d'arriver ? (stoppe l'indicateur de frappe)
  var magosReplied = false;

  function fmtTime(ts) {
    var d = new Date((ts || 0) * 1000);
    function p(n) { return (n < 10 ? "0" : "") + n; }
    return p(d.getHours()) + ":" + p(d.getMinutes());
  }

  function aquilaSVG() {
    return '<svg viewBox="0 0 100 100" aria-hidden="true">' +
      '<g fill="none" stroke="#36c46a" stroke-width="5">' +
      '<path d="M50 22 L50 78"/>' +
      '<path d="M50 30 C34 16 16 18 10 32 C24 33 32 44 38 52"/>' +
      '<path d="M50 30 C66 16 84 18 90 32 C76 33 68 44 62 52"/>' +
      '</g><circle cx="50" cy="50" r="4" fill="#36c46a"/></svg>';
  }

  // Affiche une bulle (avec fade-in via classe CSS). Retourne true si réellement rendue.
  function appendBubble(entry) {
    if (!entry || !entry.id) entry = Object.assign({}, entry, { id: "x" + Math.random() });
    var isMagos = entry.de === "magos";
    // dédupe par id si déjà rendu
    if (renderedIds.has(entry.id)) return false;
    renderedIds.add(entry.id);

    var row = document.createElement("div");
    row.className = "bubble-row " + (isMagos ? "magos" : "visiteur");

    var who = isMagos ? "Magos" : (entry.nom && entry.nom.trim() ? entry.nom.trim() : "Visiteur");

    if (isMagos) {
      var avatar = document.createElement("div");
      avatar.className = "avatar";
      avatar.innerHTML = aquilaSVG();
      row.appendChild(avatar);
    }

    var bubble = document.createElement("div");
    bubble.className = "bubble";
    var whoEl = document.createElement("span");
    whoEl.className = "who";
    whoEl.textContent = who;
    bubble.appendChild(whoEl);

    var textEl = document.createElement("span");
    textEl.className = "text";
    bubble.appendChild(textEl);

    var tsEl = document.createElement("span");
    tsEl.className = "ts";
    tsEl.textContent = fmtTime(entry.ts);
    bubble.appendChild(tsEl);

    row.appendChild(bubble);
    chatLog.appendChild(row);

    // Typing effect progressif pour les messages du Magos ; sinon texte direct.
    if (isMagos && !reducedMotion()) {
      typeText(textEl, entry.message || "");
    } else {
      textEl.textContent = entry.message || "";
    }

    chatLog.scrollTop = chatLog.scrollHeight;
    return true;
  }

  function typeText(el, text) {
    // Reveal progressif caractère par caractère (effet terminal binaire).
    var i = 0;
    var speed = Math.max(8, Math.min(28, 600 / Math.max(1, text.length)));
    (function step() {
      if (i <= text.length) {
        el.textContent = text.slice(0, i);
        i++;
        chatLog.scrollTop = chatLog.scrollHeight;
        setTimeout(step, speed);
      }
    })();
  }

  function reducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  // Affiche l'indicateur de frappe du Magos (puis le cache après délai ou à la réponse)
  var typingTimer = null;
  function showTyping() {
    typingIndicator.hidden = false;
    chatLog.scrollTop = chatLog.scrollHeight;
    if (typingTimer) clearTimeout(typingTimer);
    typingTimer = setTimeout(hideTyping, TYPING_INDICATOR_MS);
  }
  function hideTyping() {
    typingIndicator.hidden = true;
    if (typingTimer) { clearTimeout(typingTimer); typingTimer = null; }
  }

  // Envoi d'un message visiteur (HTTP POST ; le serveur le push aux clients)
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var message = msgInput.value.trim();
    if (!message) return;
    var nom = nomInput.value.trim();
    transmitBtn.disabled = true;

    fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nom: nom, message: message })
    })
      .then(function (r) {
        if (!r.ok) throw new Error("bad status " + r.status);
        msgInput.value = "";
        showTyping(); // simulation : « Le Magos retranscrit… »
      })
      .catch(function () {
        if (lastSyncEl) lastSyncEl.textContent = "échec envoi";
      })
      .finally(function () { transmitBtn.disabled = false; });
  });

  // --- TEMPS RÉEL via SocketIO (+ polling de secours pour garantir réception) ---
  function markSync(mode) {
    if (lastSyncEl) lastSyncEl.textContent = fmtTime(Date.now() / 1000) + (mode ? " (" + mode + ")" : "");
  }

  // Polling de secours : même si le WebSocket échoue, on récupère l'historique
  // toutes les 2s. Combine avec le push socketio (dedupe par id) -> jamais de perte.
  var POLL_FALLBACK_MS = 2000;
  function refresh() {
    fetch("/api/contact", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (list) {
        var newMagos = false;
        (list || []).forEach(function (entry) { if (appendBubble(entry)) newMagos = true; });
        if (newMagos) hideTyping();
        markSync("polling");
      })
      .catch(function () { if (lastSyncEl) lastSyncEl.textContent = "échec synchro"; });
  }

  if (window.io) {
    try {
      var socket = io();
      socket.on("historique", function (list) {
        (list || []).forEach(function (entry) { appendBubble(entry); });
        markSync("temps réel");
      });
      socket.on("nouvelle_reponse", function (entry) {
        if (appendBubble(entry)) hideTyping();
        markSync("temps réel");
      });
      socket.on("nouveau_visiteur", function () { markSync("temps réel"); });
      socket.on("connect", function () { markSync("temps réel"); });
      socket.on("disconnect", function () { if (lastSyncEl) lastSyncEl.textContent = "canal fermé — repli polling"; });
      // polling de secours en parallèle (silencieux, garantit la réception)
      refresh();
      setInterval(refresh, POLL_FALLBACK_MS);
    } catch (err) {
      console.warn("SocketIO error, polling seul:", err);
      refresh();
      setInterval(refresh, POLL_FALLBACK_MS);
    }
  } else {
    console.warn("SocketIO indisponible — repli sur polling.");
    refresh();
    setInterval(refresh, POLL_FALLBACK_MS);
  }

  // --- Animation : aquila binaire (aigle impérial en 0/1 qui scintillent) ---
  // Motif aquila : '#' = pixel de l'aigle, ' ' = vide. Les pixels '#' affichent
  // un 0/1 aléatoire qui change à chaque frame -> l'aigle semble "fait de binaire".
  var AQUILA = [
    "........########################........",
    "......##############################......",
    ".....######....................######.....",
    "....####..........................####....",
    "...###..............##..............###...",
    "..####............######............####..",
    "..###...........########.............###..",
    ".####..........##########............####.",
    ".###..........############............###.",
    "####.........##############...........####",
    "####........########################....####",
    "####.......########################....####",
    ".####.....########################....####.",
    ".####....########################......####.",
    "..###...########################........###..",
    "..###..##################..##..........###..",
    "...##.################......###.........##...",
    "...##.##############..........##........##...",
    "....##.###########............##.......##....",
    ".....##.##########..............##.....##.....",
    "......##.#########................##...##......",
    "......##.#######..................##.##.......",
    ".......##.#####....................###........",
    "........##.###.....................###........",
    ".........##.##.....................##.........",
    "..........###.....................###.........",
    "..........###.....................###.........",
    "...........##.....................##..........",
    "............................................",
    "............................................"
  ];

  function startAquila(canvas) {
    var ctx = canvas.getContext("2d");
    var rows = AQUILA.length, cols = AQUILA[0].length;
    var cellW = canvas.width / cols, cellH = canvas.height / rows;
    ctx.font = Math.floor(cellH * 0.95) + "px 'Share Tech Mono', monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var y = 0; y < rows; y++) {
        var line = AQUILA[y];
        for (var x = 0; x < cols; x++) {
          if (line[x] === "#") {
            var bit = Math.random() < 0.5 ? "0" : "1";
            // léger scintillement d'opacité pour l'effet "vivant"
            ctx.globalAlpha = 0.55 + Math.random() * 0.45;
            ctx.fillStyle = "#36c46a";
            ctx.fillText(bit, x * cellW + cellW / 2, y * cellH + cellH / 2);
          }
        }
      }
      ctx.globalAlpha = 1;
    }
    draw();
    setInterval(draw, 140);
  }

  function startAquilas() {
    document.querySelectorAll(".aquila-canvas").forEach(function (cv) { startAquila(cv); });
  }
  startAquilas();
})();

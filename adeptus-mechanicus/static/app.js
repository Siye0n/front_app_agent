/* ============================================================
   Adeptus Mechanicus — logique du chat de contact (cote serveur)
   - Charge les messages existants via GET /api/contact
   - Envoie un nouveau message via POST /api/contact
   Aucune reponse automatique : le Magos repond hors ligne en
   lisant messages.json.
   ============================================================ */

(function () {
  "use strict";

  const form = document.getElementById("contactForm");
  const nomInput = document.getElementById("nom");
  const msgInput = document.getElementById("message");
  const submitBtn = document.getElementById("submitBtn");
  const formStatus = document.getElementById("formStatus");
  const messagesList = document.getElementById("messagesList");

  // Echappement HTML pour eviter l'injection de markup dans la liste.
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }

  // Formatage d'un timestamp (secondes) en date lisible fr.
  function formatTs(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  // Cree un element <li> pour un message.
  function buildMessageNode(m) {
    const li = document.createElement("li");
    li.className = "msg";

    const meta = document.createElement("div");
    meta.className = "msg-meta";

    const nom = document.createElement("span");
    nom.className = "msg-nom";
    nom.textContent = m.nom || "Inconnu";

    const date = document.createElement("span");
    date.className = "msg-date";
    date.textContent = formatTs(m.ts);

    meta.appendChild(nom);
    meta.appendChild(date);

    const text = document.createElement("p");
    text.className = "msg-text";
    text.textContent = m.message || "";

    li.appendChild(meta);
    li.appendChild(text);
    return li;
  }

  // Rend la liste des messages (du plus recent au plus ancien).
  function renderMessages(messages) {
    messagesList.innerHTML = "";
    if (!messages || messages.length === 0) {
      const empty = document.createElement("li");
      empty.className = "messages-empty";
      empty.textContent = "Aucune transmission pour l'instant. Sois le premier à contacter le Magos.";
      messagesList.appendChild(empty);
      return;
    }
    messages.forEach(function (m) {
      messagesList.appendChild(buildMessageNode(m));
    });
  }

  // Recupere les messages existants depuis le serveur.
  async function loadMessages() {
    try {
      const res = await fetch("/api/contact", { method: "GET" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      renderMessages(data);
    } catch (err) {
      messagesList.innerHTML = "";
      const errLi = document.createElement("li");
      errLi.className = "messages-empty";
      errLi.textContent = "Impossible de charger les transmissions. Réessaie plus tard.";
      messagesList.appendChild(errLi);
    }
  }

  // Envoi du formulaire.
  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const nom = nomInput.value.trim();
    const message = msgInput.value.trim();

    formStatus.className = "form-status";
    formStatus.textContent = "";

    if (!message) {
      formStatus.className = "form-status err";
      formStatus.textContent = "Le message est requis pour la transmission.";
      msgInput.focus();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Transmission…";

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nom: nom, message: message }),
      });

      if (res.status === 400) {
        formStatus.className = "form-status err";
        formStatus.textContent = "Message vide — transmission refusée.";
      } else if (res.ok) {
        const json = await res.json();
        formStatus.className = "form-status ok";
        formStatus.textContent =
          "Transmission enregistrée (réf #" + json.id + ") — le Magos répondra par canal sécurisé.";
        msgInput.value = "";
        // Recharge la liste pour afficher le message cote serveur.
        await loadMessages();
      } else {
        throw new Error("HTTP " + res.status);
      }
    } catch (err) {
      formStatus.className = "form-status err";
      formStatus.textContent = "Erreur de transmission. Réessaie plus tard.";
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Transmettre";
    }
  });

  // Bandeau binaire animé (ambiance machine).
  const banner = document.getElementById("binaryBanner");
  if (banner) {
    let chars = "";
    const TARGET = 220;
    function tick() {
      // Decale et ajoute un nouveau caractere aleatoire 0/1.
      chars = chars.slice(1) + (Math.random() < 0.5 ? "0" : "1");
      banner.textContent = chars;
    }
    for (let i = 0; i < TARGET; i++) chars += Math.random() < 0.5 ? "0" : "1";
    banner.textContent = chars;
    setInterval(tick, 90);
  }

  // Chargement initial.
  loadMessages();
})();

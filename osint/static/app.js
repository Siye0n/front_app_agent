/* Front-end OSINT WHOIS : upload CSV, scan WHOIS, dashboard néon. */

(function () {
  "use strict";

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("csv-input");
  const fileInfo = document.getElementById("file-info");
  const domainsInput = document.getElementById("domains-input");
  const scanBtn = document.getElementById("scan-btn");
  const clearBtn = document.getElementById("clear-btn");
  const progress = document.getElementById("progress");
  const progressFill = document.getElementById("progress-fill");
  const progressLabel = document.getElementById("progress-label");
  const statusEl = document.getElementById("status");
  const metricsEl = document.getElementById("metrics");
  const resultsEl = document.getElementById("results");
  const tbodyEl = document.getElementById("tbody");

  let selectedFile = null;

  /* Active le bouton scan si un fichier est choisi OU des domaines saisis. */
  function refreshScanState() {
    const hasDomains = domainsInput && domainsInput.value.trim().length > 0;
    scanBtn.disabled = !(selectedFile || hasDomains);
  }

  /* ---------- Helpers ---------- */

  function setStatus(msg, kind) {
    statusEl.textContent = msg || "";
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  let _typeTimer = null;
  function typeStatus(msg, kind) {
    if (_typeTimer) clearInterval(_typeTimer);
    setStatus("", kind);
    let i = 0;
    const target = msg || "";
    _typeTimer = setInterval(function () {
      statusEl.textContent = target.slice(0, i++);
      if (i > target.length) { clearInterval(_typeTimer); _typeTimer = null; }
    }, 12);
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function fmtList(arr) {
    if (!arr || !arr.length) return '<span class="muted">—</span>';
    const items = arr.slice(0, 3).map(function (s) { return escapeHtml(s); }).join(", ");
    const extra = arr.length > 3 ? ' <span class="muted">(+' + (arr.length - 3) + ')</span>' : "";
    return items + extra;
  }

  function statusBadge(state) {
    const labels = {
      active: "ACTIF",
      expired: "EXPIRÉ",
      soon: "EXPIRE BIENTÔT",
      unknown: "INCONNU",
      error: "ERREUR",
    };
    const label = labels[state] || "INCONNU";
    return '<span class="badge ' + state + '">' + label + "</span>";
  }

  /* ---------- Upload ---------- */

  function handleFile(file) {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".csv") && file.type !== "text/csv" && file.type !== "text/plain") {
      setStatus("Format non supporté : un fichier .csv est requis.", "error");
      return;
    }
    selectedFile = file;
    fileInfo.hidden = false;
    fileInfo.innerHTML = 'Fichier : <span class="name">' + escapeHtml(file.name) +
      "</span> (" + (file.size || 0) + " o)";
    refreshScanState();
    setStatus("Fichier prêt. Lancez le scan.", "ok");
  }

  if (domainsInput) {
    domainsInput.addEventListener("input", function () {
      refreshScanState();
    });
  }

  dropzone.addEventListener("click", function (e) {
    // Ne déclenche pas si on clique sur le label (qui gère déjà l'input).
    if (e.target.tagName !== "LABEL" && e.target.tagName !== "INPUT") {
      fileInput.click();
    }
  });
  fileInput.addEventListener("change", function () {
    if (fileInput.files && fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  ["dragenter", "dragover"].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault();
      if (ev === "dragleave" && dropzone.contains(e.relatedTarget)) return;
      dropzone.classList.remove("dragover");
    });
  });
  dropzone.addEventListener("drop", function (e) {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files[0]) handleFile(dt.files[0]);
  });

  clearBtn.addEventListener("click", resetAll);

  function resetAll() {
    selectedFile = null;
    fileInput.value = "";
    fileInfo.hidden = true;
    fileInfo.innerHTML = "";
    if (domainsInput) domainsInput.value = "";
    refreshScanState();
    progress.hidden = true;
    metricsEl.hidden = true;
    resultsEl.hidden = true;
    tbodyEl.innerHTML = "";
    setStatus("", null);
    clearBtn.hidden = true;
  }

  /* ---------- Scan ---------- */

  scanBtn.addEventListener("click", function () {
    // Si des domaines sont saisis (sans fichier), on fabrique un CSV synthétique.
    let fd;
    if (selectedFile) {
      fd = new FormData();
      fd.append("csv", selectedFile, selectedFile.name);
    } else if (domainsInput && domainsInput.value.trim()) {
      const text = domainsInput.value
        .split(/[\n,;\s]+/)          // une ou plusieurs lignes / virgules / espaces
        .map(function (s) { return s.trim().toLowerCase(); })
        .filter(Boolean)
        .join("\n");
      const blob = new Blob([text], { type: "text/csv" });
      fd = new FormData();
      fd.append("csv", blob, "domains.csv");
    } else {
      return;
    }

    scanBtn.disabled = true;
    clearBtn.hidden = false;
    progress.hidden = false;
    metricsEl.hidden = true;
    resultsEl.hidden = true;
    tbodyEl.innerHTML = "";
    typeStatus("Scan WHOIS en cours…");

    progressFill.style.width = "20%";
    progressLabel.textContent = "Interrogation WHOIS…";

    fetch("/api/scan", { method: "POST", body: fd })
      .then(function (resp) {
        return resp.json().then(function (body) {
          if (!resp.ok) throw new Error(body.error || ("Erreur HTTP " + resp.status));
          return body;
        });
      })
      .then(function (data) {
        progressFill.style.width = "100%";
        progressLabel.textContent = data.domaines_scannes + " / " + data.domaines_scannes + " domaines scannés";
        renderDashboard(data);
        typeStatus("Scan terminé : " + data.count + " résultat(s).", "ok");
      })
      .catch(function (err) {
        progressFill.style.width = "0%";
        progressLabel.textContent = "";
        typeStatus("Erreur réseau : " + err.message, "error");
      })
      .finally(function () {
        scanBtn.disabled = false;
      });
  });

  /* ---------- Rendu dashboard ---------- */

  function renderDashboard(data) {
    const results = data.resultats || [];
    let ok = 0, fail = 0, soon = 0;

    tbodyEl.innerHTML = "";
    results.forEach(function (r) {
      const expired = r.expiry_state === "expired";
      const isSoon = r.expiry_state === "soon";
      const isError = r.expiry_state === "error" || r.erreur;
      if (isError) fail++;
      else ok++;
      if (isSoon) soon++;

      const tr = document.createElement("tr");
      tr.innerHTML =
        '<td class="domain-cell">' + escapeHtml(r.domaine) + "</td>" +
        "<td>" + escapeHtml(r.registrar) + "</td>" +
        "<td>" + escapeHtml(r.creation_date) + "</td>" +
        "<td>" + escapeHtml(r.expiration_date) + "</td>" +
        "<td>" + statusBadge(r.expiry_state) + "</td>" +
        '<td class="wrap ns-list">' + fmtList(r.name_servers) + "</td>" +
        "<td>" + (r.erreur ? '<span class="err-cell">' + escapeHtml(r.erreur) + "</span>"
                             : '<span class="muted">—</span>') + "</td>";
      tbodyEl.appendChild(tr);
    });

    document.getElementById("m-total").textContent = data.count;
    document.getElementById("m-ok").textContent = ok;
    document.getElementById("m-fail").textContent = fail;
    document.getElementById("m-soon").textContent = soon;

    metricsEl.hidden = false;
    resultsEl.hidden = false;
  }

  /* ---------- Chargement initial (résultats persistés) ---------- */

  fetch("/api/results")
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (data && data.resultats && data.resultats.length) {
        // Pas de fichier sélectionné, mais on affiche d'anciens résultats.
        progress.hidden = true;
        renderDashboard(data);
        setStatus("Derniers résultats chargés (scan précédent).", null);
      }
    })
    .catch(function () { /* pas de résultats -> rien à afficher */ });
})();

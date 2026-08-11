/* Front-end OSINT : appelle /api/entreprises et affiche un tableau. */

(function () {
  "use strict";

  const villeEl = document.getElementById("ville");
  const limitEl = document.getElementById("limit");
  const btnEl = document.getElementById("rechercher");
  const statusEl = document.getElementById("status");
  const resultsEl = document.getElementById("results");
  const titleEl = document.getElementById("results-title");
  const tbodyEl = document.getElementById("tbody");

  /** Affiche un message d'état (erreur si `isError`). */
  function setStatus(message, isError) {
    statusEl.textContent = message || "";
    statusEl.classList.toggle("error", Boolean(isError));
  }

  /** Échappe le HTML pour éviter l'injection depuis la réponse. */
  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  /** Construit une cellule site web cliquable, ou "—" si absent. */
  function siteCell(site) {
    if (site) {
      const safe = escapeHtml(site);
      return '<a href="' + safe + '" target="_blank" rel="noopener noreferrer">' + safe + "</a>";
    }
    return '<span class="muted">—</span>';
  }

  /** Rend le tableau à partir de la réponse JSON. */
  function renderTable(data) {
    tbodyEl.innerHTML = "";
    data.entreprises.forEach(function (e) {
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + escapeHtml(e.nom) + "</td>" +
        "<td>" + escapeHtml(e.adresse) + "</td>" +
        "<td>" + siteCell(e.site_web) + "</td>";
      tbodyEl.appendChild(tr);
    });
    titleEl.textContent = data.count + " entreprise(s) à " + data.ville;
    resultsEl.hidden = false;
  }

  /** Lance la recherche via fetch vers l'API. */
  function rechercher() {
    const ville = villeEl.value.trim();
    if (!ville) {
      setStatus("Veuillez saisir une ville.", true);
      resultsEl.hidden = true;
      return;
    }
    const limit = limitEl.value || "10";

    btnEl.disabled = true;
    setStatus("Recherche en cours…", false);

    const url = "/api/entreprises?ville=" +
      encodeURIComponent(ville) + "&limit=" + encodeURIComponent(limit);

    fetch(url)
      .then(function (resp) {
        return resp.json().then(function (body) {
          if (!resp.ok) {
            throw new Error(body.error || ("Erreur HTTP " + resp.status));
          }
          return body;
        });
      })
      .then(function (data) {
        renderTable(data);
        setStatus("", false);
      })
      .catch(function (err) {
        setStatus("Erreur : " + err.message, true);
        resultsEl.hidden = true;
      })
      .finally(function () {
        btnEl.disabled = false;
      });
  }

  btnEl.addEventListener("click", rechercher);
  // Permet de valider avec Entrée depuis le champ ville.
  villeEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") rechercher();
  });
})();

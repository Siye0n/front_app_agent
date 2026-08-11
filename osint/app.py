"""
Serveur Flask OSINT entreprises.

Ce module expose une petite API qui récupère les N premières entreprises
d'une ville et renvoie leur nom, adresse et site web (si disponible).

Deux sources de données sont abstraites derrière l'interface `CompanySource` :
  - MockSource   : données de démo déterministes (par défaut, aucune clé API).
  - PappersSource : interroge l'API Pappers si la variable d'env PAPPERS_API_KEY
                    est définie ; sinon cette source n'est jamais instanciée.

Le serveur sélectionne la source à l'instanciation : Pappers si la clé est
présente, Mock sinon. La clé API ne quitte jamais le serveur.
"""

from __future__ import annotations

import hashlib
import os
import random
import urllib.parse

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# URL de l'API Pappers (recherche d'entreprises).
PAPPERS_API_URL = "https://api.pappers.fr/v2/recherche"


class CompanySource:
    """Interface abstraite d'une source de données d'entreprises.

    Toute implémentation concrète doit fournir `get_companies(ville, limit)`
    et renvoyer une liste de dicts normalisés :
        {"nom": str, "adresse": str, "site_web": str | None}
    """

    def get_companies(self, ville: str, limit: int) -> list[dict]:
        """Retourne jusqu'à `limit` entreprises pour la ville donnée.

        :param ville: nom de la ville (ex: "Paris").
        :param limit: nombre maximum d'entreprises à renvoyer.
        :return: liste de dicts {nom, adresse, site_web}.
        """
        raise NotImplementedError


class MockSource(CompanySource):
    """Source de démonstration déterministe (aucune clé API, aucun réseau).

    Les données générées sont reproductibles : un seed est dérivé du nom de
    la ville via un hash, garantissant que "Paris" produit toujours le même
    jeu de résultats. Une partie des entreprises se voit attribuer un
    `site_web` à None pour refléter la réalité (certaines boîtes n'ont pas
    de site).
    """

    # Préfixes / suffixes plausibles pour composer des noms d'entreprises.
    _PREFIXES = [
        "Atlas", "Nova", "Quantum", "Helios", "Vertex", "Lumen", "Orion",
        "Cobalt", "Meridian", "Aurora", "Polaris", "Synthex", "Borealis",
        "Tessera", "Vectra", "Nimbus", "Ardent", "Cyane", "Lagune", "Solstice",
    ]
    _SUFFIXES = [
        "Solutions", "Industries", "Group", "Technologies", "Logistique",
        "Consulting", "Digital", "Énergie", "Mobilité", "Santé", "Finance",
        "Éditions", "Constructions", "Communication", "Robotics",
    ]
    # Types de voies pour des adresses réalistes.
    _VOIES = [
        "rue", "avenue", "boulevard", "place", "impasse", "quai", "allée",
    ]
    _NOMS_VOIES = [
        "de la République", "Victor Hugo", "Jean Jaurès", "des Lilas",
        "du Général Leclerc", "de la Gare", "des Tilleuls", "Pasteur",
        "de la Fontaine", "du Commerce", "des Vignes", "du Lavoir",
    ]

    def get_companies(self, ville: str, limit: int) -> list[dict]:
        """Génère `limit` entreprises déterministes et uniques pour la ville.

        Le seed est dérivé de la ville (en minuscules, normalisée) afin que
        deux requêtes identiques produisent exactement le même résultat. Pour
        garantir l'unicité de chaque entreprise sans perdre le déterminisme,
        chaque entrée est tirée à partir d'un sous-seed = base + index + salt ;
        en cas de collision (même nom+adresse déjà vu), on incrémente le salt
        de façon déterministe jusqu'à obtenir une entrée inédite.
        """
        # Normalise la ville pour un seed stable (minuscules, accents retirés).
        seed_str = self._normalize(ville)
        # Hash SHA-256 -> entier pour seeder le RNG de base.
        seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16) % (2 ** 32)

        code_postal = self._code_postal_for(ville, random.Random(seed_int))
        entreprises: list[dict] = []
        used: set[tuple[str, str]] = set()

        for i in range(limit):
            salt = 0
            while True:
                # Sous-seed déterministe par (index, salt).
                sub = random.Random((seed_int + i * 1000003 + salt) & 0xFFFFFFFF)
                nom = f"{sub.choice(self._PREFIXES)} {sub.choice(self._SUFFIXES)}"
                numero = sub.randint(1, 220)
                voie = f"{sub.choice(self._VOIES)} {sub.choice(self._NOMS_VOIES)}"
                adresse = f"{numero} {voie}, {code_postal} {ville.title()}"

                if (nom, adresse) not in used:
                    break
                salt += 1  # collision déterministe -> on ré-essaie

            used.add((nom, adresse))

            # ~70 % des entreprises ont un site web, les autres None.
            if sub.random() < 0.7:
                slug = self._slug(nom) + self._slug(ville)
                site_web = f"https://www.{slug}.fr"
            else:
                site_web = None

            entreprises.append({
                "nom": nom,
                "adresse": adresse,
                "site_web": site_web,
            })
        return entreprises

    @staticmethod
    def _normalize(ville: str) -> str:
        """Met la ville en minuscules et retire les accents/espaces superflus."""
        import unicodedata
        v = unicodedata.normalize("NFKD", ville.lower())
        v = "".join(c for c in v if not unicodedata.combining(c))
        return v.strip()

    @staticmethod
    def _slug(text: str) -> str:
        """Transforme un texte en slug alphanumérique simple."""
        import unicodedata
        v = unicodedata.normalize("NFKD", text.lower())
        v = "".join(c for c in v if not unicodedata.combining(c))
        v = "".join(c if c.isalnum() else "" for c in v)
        return v

    @staticmethod
    def _code_postal_for(ville: str, rng: random.Random) -> str:
        """Fabrique un code postal plausible (5 chiffres) pour la ville.

        On dérive un préfixe stable à partir du hash de la ville pour que le
        code postal reste le même d'une requête à l'autre.
        """
        prefix = 10 + (hash(ville.lower()) % 89)  # 10..98
        suffix = rng.randint(0, 999)
        return f"{prefix:02d}{suffix:03d}"


class PappersSource(CompanySource):
    """Source réelle basée sur l'API Pappers (nécessite PAPPERS_API_KEY).

    Cette source n'est instanciée QUE si la clé est définie. Elle interroge
    l'endpoint /v2/recherche avec la ville et le nombre demandés, puis mappe
    les résultats vers le format normalisé. La clé API reste côté serveur et
    n'apparaît jamais dans la réponse.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("PappersSource nécessite une clé API Pappers.")
        self.api_key = api_key

    def get_companies(self, ville: str, limit: int) -> list[dict]:
        """Interroge Pappers et mappe les résultats vers le format normalisé.

        :raises requests.RequestException: en cas d'échec réseau/HTTP.
        """
        # Limite Pappers : 200 par page ; on borne à ce que l'on demande.
        params = {
            "api_token": self.api_key,
            "ville": ville,
            "par_page": max(1, min(limit, 200)),
            "page": 1,
        }
        resp = requests.get(PAPPERS_API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        entreprises: list[dict] = []
        for ent in data.get("entreprises", [])[:limit]:
            nom = ent.get("nom_entreprise") or ent.get("denomination") or "—"
            adresse = self._build_adresse(ent)
            site_web = ent.get("site_web") or None
            entreprises.append({
                "nom": nom,
                "adresse": adresse,
                "site_web": site_web,
            })
        return entreprises

    @staticmethod
    def _build_adresse(ent: dict) -> str:
        """Recompose une adresse lisible à partir des champs Pappers."""
        parts = [
            ent.get("numero_voie"),
            ent.get("type_voie"),
            ent.get("libelle_voie"),
            ent.get("code_postal"),
            ent.get("ville"),
        ]
        # Filtre les valeurs vides et joint.
        return ", ".join(str(p) for p in parts if p)


def _build_source() -> CompanySource:
    """Sélectionne la source : Pappers si la clé est définie, sinon Mock.

    La clé n'est jamais exposée. Si Pappers est configuré mais renvoie une
    erreur d'authentification/crédits (401), on bascule silencieusement sur
    MockSource pour ne jamais servir un site cassé (la donnée mock reste
    disponible en attendant que des crédits soient ajoutés).
    """
    api_key = os.getenv("PAPPERS_API_KEY")
    if api_key:
        try:
            src = PappersSource(api_key)
            # Test léger : une requête minimale pour détecter clé invalide /
            # crédits épuisés avant de servir. En cas d'échec, fallback Mock.
            src.get_companies("Paris", 1)
            return src
        except Exception:
            # clé invalide ou crédits épuisés -> on s'appuie sur le mock
            return MockSource()
    return MockSource()


# Source choisie une fois au démarrage du serveur.
SOURCE: CompanySource = _build_source()


def _clamp_limit(raw: str | None) -> int:
    """Valide et borne le paramètre `limit` (1..50, défaut 10)."""
    try:
        limit = int(raw) if raw is not None else 10
    except (TypeError, ValueError):
        limit = 10
    return max(1, min(limit, 50))


@app.route("/")
def index():
    """Sert la page d'accueil (formulaire de recherche)."""
    return render_template("index.html")


@app.route("/api/entreprises")
def api_entreprises():
    """Endpoint API : renvoie les entreprises d'une ville.

    Query params :
      - ville  (requis) : nom de la ville.
      - limit  (optionnel, défaut 10, max 50) : nombre d'entreprises.

    Réponse JSON :
      {"ville": str, "count": int, "entreprises": [ {nom, adresse, site_web}, ... ]}
    """
    ville = (request.args.get("ville") or "").strip()
    if not ville:
        return jsonify({"error": "Le paramètre 'ville' est requis."}), 400

    limit = _clamp_limit(request.args.get("limit"))
    try:
        entreprises = SOURCE.get_companies(ville, limit)
    except Exception as exc:  # noqa: BLE001 - on veut capturer toute erreur réseau/source
        return jsonify({"error": f"Erreur de la source de données : {exc}"}), 502

    return jsonify({
        "ville": ville,
        "count": len(entreprises),
        "entreprises": entreprises,
    })


if __name__ == "__main__":
    # Port 5000, debug=False en production (OK pour test local).
    app.run(host="127.0.0.1", port=5000, debug=False)

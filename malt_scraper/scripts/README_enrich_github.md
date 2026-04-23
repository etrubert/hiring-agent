# GitHub Enrichment — Scraper complémentaire Malt

Enrichit les profils Malt avec les données GitHub publiques des freelances
qui ont déclaré leur compte GitHub sur leur profil Malt.

## À quoi ça sert

Pour chaque freelance Malt ayant un lien GitHub, récupère :
- **Bio** GitHub + localisation déclarée
- **Nombre de repos publics** + nombre de followers
- **Top 5 repos non-fork** (triés par stars) avec nom, description, langage, date, URL

Permet au jury/recruteur de voir **ce que le freelance produit réellement**
au-delà de ce qu'il déclare sur Malt.

## Prérequis

- Fichier source : `data/final/malt-1.json` doit exister (généré par `main.py` ou `scripts/reparse_cached.py`)
- Les profils doivent avoir un champ `github_url` non vide
  (extrait automatiquement par `src/scraper/profile_scraper.py::_external_links()`)
- **Pas de clé API requise** — utilise l'API publique GitHub

## Utilisation

```bash
cd malt_scraper
python scripts/enrich_github.py
```

Sortie : `data/final/github_profiles.json`

## Format de sortie

```json
[
  {
    "name": "Aghiles A.",
    "user": "Axibord",
    "url": "https://github.com/Axibord",
    "bio": "Software Engineer — AI Engineer",
    "public_repos": 12,
    "followers": 21,
    "top_repos": [
      {
        "name": "react-typescript-starter",
        "desc": "Starter for React projects using Atomic design",
        "stars": 20,
        "lang": "JavaScript",
        "updated": "2025-07-11",
        "url": "https://github.com/Axibord/react-typescript-starter"
      }
    ]
  }
]
```

## Limites

- **Rate limit non-authentifié** : 60 requêtes/h (2 requêtes par utilisateur → ~30 freelances max par run). Largement suffisant pour le volume Malt actuel (~10 profils avec GitHub).
- Pour dépasser : ajouter un `GITHUB_TOKEN` dans l'en-tête `Authorization` (5000 req/h).
- Repos privés non récupérables (API publique uniquement).
- Forks ignorés (on veut ce que le freelance a **produit**, pas cloné).

## Fichiers liés

| Fichier | Rôle |
|---|---|
| `scripts/enrich_github.py` | Ce script |
| `src/scraper/profile_scraper.py` | Extrait les URLs GitHub depuis le HTML Malt (`_external_links()`) |
| `data/final/malt-1.json` | Source — profils Malt avec `github_url` |
| `data/final/github_profiles.json` | Sortie — enrichissement GitHub |

# hackathon_scraper

Scraper multi-plateforme pour trouver des hackathons AI/ML pertinents.

## Règle de filtrage

Un hackathon est gardé si :

    (theme_is_ai AND has_target_role_in_people) OR has_specific_tool

Les 4 rôles ciblés sont listés dans [sources/target_roles.yaml](sources/target_roles.yaml) :

- Agent Builder
- AI Engineering Manager
- Senior AI Engineer
- Senior Data Scientist

Les outils spécifiques (LangChain, MCP, Claude, etc.) sont dans [sources/skills.yaml](sources/skills.yaml) — la mention d'un seul suffit à garder la ligne, même sans rôle détecté.

## Plateformes

Actives sans clé API :

| Plateforme    | Source                                   |
|---------------|------------------------------------------|
| Devpost       | JSON public `/api/hackathons`            |
| MLH           | HTML de `mlh.io/seasons/...`             |
| HackerEarth   | JSON `/chrome-ext/events/` + fallback HTML |
| HackerNews    | Algolia `search_by_date`                 |
| AI Tinkerers  | HTML des chapitres city                  |

Stubs (activer dans `sources/platforms.yaml` + clé dans `.env`) :

| Plateforme  | Ce qu'il faut                         |
|-------------|---------------------------------------|
| Eventbrite  | `EVENTBRITE_TOKEN`                    |
| Reddit      | (clé optionnelle)                     |
| Tavily      | `TAVILY_API_KEY`                      |
| Luma        | Playwright ou API officielle          |
| LinkedIn    | Cookie `li_at` authentifié            |
| Meetup      | Auth GraphQL                          |

## Installation

```bash
cd hackathon_scraper
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # optionnel — seulement si tu veux activer les stubs
```

## Utilisation

```bash
python main.py                              # plateformes enabled=true dans platforms.yaml
python main.py --platforms devpost,mlh      # liste explicite
python main.py --keep-all                   # écrit tout, sans le filtre strict
python main.py --min-score 50               # seuil plus exigeant
python main.py --excel                      # ajoute un .xlsx multi-onglets
python main.py --resume                     # reprend le dernier snapshot raw
```

## Sorties

Dans [data/final/](data/final/) :

- `hackathons_<stamp>.csv` — une ligne par hackathon avec score, rôles, outils, reasons
- `people_<stamp>.csv` — une ligne par personne (juge/mentor) avec `target_role` résolu
- `companies_<stamp>.csv` — une ligne par sponsor/partenaire
- `hackathons_<stamp>.xlsx` (si `--excel`) — onglets par plateforme et par rôle

Snapshots intermédiaires dans [data/raw/](data/raw/) et [data/filtered/](data/filtered/).

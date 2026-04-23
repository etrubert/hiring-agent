# GitHub Candidate Sourcing — Mirakl AI/ML Talent

Outil de sourcing automatisé qui cherche sur GitHub des candidats correspondant
à 4 profils cibles de Mirakl (AI/ML), les enrichit via l'API GitHub, les score
avec un LLM, puis exporte un CSV classé.

## À quoi ça sert

Pour chaque rôle cible, le script :
1. Recherche des utilisateurs GitHub via des requêtes ciblées (langchain, LLM, MLOps…)
2. Filtre par localisation (France) et par signaux AI dans le code / la bio
3. Enrichit chaque candidat (repos, stars, bio, langues, activité récente)
4. Demande à un LLM de noter chaque candidat (0-100) contre le rôle
5. Classe et garde le **top 5 par rôle** (20 candidats au total) dans un CSV

## Rôles ciblés

Les 4 rôles sont définis dans [search_candidates.py:ROLES](search_candidates.py) :

| Rôle | Expérience | Signaux recherchés |
|---|---|---|
| `agent_builder` | 3-5 ans | Agents LLM, LangGraph, CrewAI, AutoGen |
| `ai_engineering_manager` | 7-20 ans | Leadership ML, équipes, architecture |
| `senior_ai_engineer` | 5-15 ans | LLM en prod, RAG, fine-tuning, MLOps |
| `data_scientist_senior` | 6-12 ans | ML classique, feature eng., modèles métiers |

## Prérequis

- **Token GitHub obligatoire** (`GITHUB_TOKEN` dans `.env` ou env var)
  → API non-auth = 60 req/h ≠ suffisant ; auth = 5000 req/h
- **Clé LLM** (Anthropic ou Gemini) pour le scoring — lue par `llm_utils.py`
- Python 3.10+

### Installation du token

```bash
./setup_token.sh          # prompt interactif (masque la saisie)
# ou manuellement :
echo "GITHUB_TOKEN=ghp_xxx" >> .env
```

## Utilisation

```bash
python search_candidates.py                 # sortie par défaut : candidates-1.csv
python search_candidates.py mon_export.csv  # sortie custom
```

Durée typique : 5-10 min (dépend du rate limit GitHub et du LLM).

## Pipeline (4 phases)

Les 4 phases sont exécutées séquentiellement dans `main()` :

| Phase | Fonction | Rôle |
|---|---|---|
| 1. Search | `phase_search()` | Interroge GitHub Search API avec les requêtes de `SEARCH_QUERIES_PER_ROLE` |
| 2. Enrich | `phase_enrich()` | Récupère profil + repos pour chaque user (8 workers parallèles) |
| 3. Score | `phase_score()` | Envoie chaque candidat au LLM avec `SCORING_PROMPT_TEMPLATE` |
| 4. Rank | `phase_rank()` | Trie par score, garde top 5 par rôle, écrit le CSV |

### Filtres appliqués avant le LLM (pour économiser les appels)

- `FRANCE_LOCATION_MARKERS` : refuse les profils hors France
- `AI_SIGNAL_KEYWORDS` : bio/repos doivent contenir au moins 1 signal AI
- `ROLE_HINT_KEYWORDS` : pré-classification par rôle avant le LLM
- `balance_pool_per_role()` : garantit qu'un rôle sous-représenté n'est pas ignoré
- `ENRICH_CAP_PER_ROLE = 60` : limite de candidats enrichis par rôle

## Format de sortie (CSV)

Colonnes de `candidates-1.csv` :

| Colonne | Description |
|---|---|
| `role` | Rôle cible matché |
| `score` | Note LLM (0-100) |
| `login` | Username GitHub |
| `name` | Nom complet |
| `location` | Localisation déclarée |
| `bio` | Bio GitHub |
| `followers` | Nombre de followers |
| `public_repos` | Nombre de repos publics |
| `top_langs` | 3 langages les + utilisés |
| `top_repos` | Top 3 repos (nom, stars) |
| `profile_url` | `https://github.com/<login>` |
| `reasoning` | Justification LLM du score |

## Fichiers du dossier

| Fichier | Rôle |
|---|---|
| [search_candidates.py](search_candidates.py) | Script principal (4 phases) |
| [setup_token.sh](setup_token.sh) | Installation interactive du `GITHUB_TOKEN` |
| [run_test.sh](run_test.sh) | Script de test (legacy — évalue des CV) |
| [candidates-1.csv](candidates-1.csv) | Exemple d'export (20 candidats × 12 colonnes) |
| `.env` | `GITHUB_TOKEN=...` (non versionné) |

## Dépendances externes (autres dossiers)

Le script importe depuis la racine du repo :
- `github._fetch_github_api` — wrapper rate-limited autour de l'API GitHub
- `llm_utils.initialize_llm_provider` — abstraction Anthropic / Gemini
- `prompt.DEFAULT_MODEL`, `prompt.MODEL_PARAMETERS` — config LLM par défaut

## Limites

- GitHub Search API : 30 req/min (auth) → le script throttle automatiquement
- Localisation = champ déclaré par l'utilisateur (peut être vide ou faux)
- Le LLM peut halluciner le score → `reasoning` doit être lu avant décision finale
- Pas de déduplication cross-rôle : un même user peut apparaître dans 2 rôles

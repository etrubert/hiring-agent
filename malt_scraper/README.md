# Malt Freelance Scraper — Sourcing IA pour Mirakl

Identifie sur Malt.fr des freelances IA correspondant aux 4 postes cibles Mirakl,
basés à Paris ou Bordeaux, avec les compétences clés et une expérience potentielle
chez un des 12 concurrents Mirakl.

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## Utilisation

```bash
python main.py                 # scrape, écrit data/final/malt-1.json + CSV + Excel
python main.py --yes           # skip le disclaimer
python main.py --max 50        # limite à 50 profils
```

## Sortie principale

`data/final/malt-1.json` — liste des freelances scrapés avec leurs missions,
avis, compétences, et flag `is_match`.

## Avertissements

- Scraper Malt viole leurs CGU → risque de ban du compte.
- Collecte de données personnelles → usage strictement interne / démo jury.
- Délais 3-8s entre requêtes obligatoires.
- Pas de revente, pas de prospection sans consentement.

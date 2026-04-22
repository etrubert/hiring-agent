#!/bin/bash
# Interactive helper to add GITHUB_TOKEN to .env safely.
# Prompts hide the token from terminal history.

set -e
cd "$(dirname "$0")"

if grep -q "^GITHUB_TOKEN=" .env 2>/dev/null; then
    echo "⚠️  GITHUB_TOKEN déjà présent dans .env."
    read -p "Le remplacer ? (y/N) " ans
    if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
        echo "Annulé."
        exit 0
    fi
    # Remove old line
    sed -i.bak '/^GITHUB_TOKEN=/d' .env && rm .env.bak
fi

echo ""
echo "Colle ton token GitHub (il sera masqué pendant la saisie) :"
read -s TOKEN
echo ""

if [[ -z "$TOKEN" ]]; then
    echo "❌ Token vide, abandon."
    exit 1
fi

if [[ ${#TOKEN} -lt 20 ]]; then
    echo "❌ Token suspect (trop court, ${#TOKEN} caractères). Abandon."
    exit 1
fi

echo "GITHUB_TOKEN=$TOKEN" >> .env
echo "✅ Token ajouté à .env (longueur: ${#TOKEN} caractères)"
echo ""
echo "Tu peux maintenant lancer : python search_candidates.py"

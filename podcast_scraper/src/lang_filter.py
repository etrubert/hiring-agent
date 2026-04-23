"""Heuristic French-language detector for podcast episodes.

No external lib: we combine three signals on title+description+channel:
  - French accents (à â ç é è ê î ï ô ù û)
  - French stopword density vs English stopword density
  - Known FR channel whitelist (forces pass)
  - Known EN channel blacklist (forces fail)

Returns True if the episode is probably French.
"""

import re
from typing import Dict

_ACCENT_RE = re.compile(r"[àâäçéèêëîïôöùûüÿœæ]", re.I)

_FR_STOPWORDS = re.compile(
    r"\b(le|la|les|un|une|des|du|de|au|aux|et|ou|mais|donc|car|ce|cette|ces|qui|que|quoi|"
    r"dont|où|nous|vous|ils|elles|avec|pour|sans|dans|sur|sous|par|plus|moins|tout|tous|"
    r"cette|celui|celle|ceux|leur|leurs|son|sa|ses|mon|ma|mes|ton|ta|tes|notre|votre|"
    r"est|sont|être|avoir|fait|faire|dit|dire|peut|pouvoir|comme|aussi|très|bien|alors|"
    r"aujourd'hui|hier|demain|épisode|invité|interview|découverte|découvrir|métier|"
    r"entreprise|recherche|équipe|données|technologie|numérique|apprentissage|modèle)\b",
    re.I,
)

_EN_STOPWORDS = re.compile(
    r"\b(the|a|an|and|or|but|if|then|else|this|that|these|those|which|who|whose|whom|"
    r"what|where|when|why|how|with|without|into|onto|from|about|over|under|through|"
    r"is|are|was|were|be|been|being|has|have|had|do|does|did|doing|will|would|should|"
    r"could|can|may|might|must|today|tomorrow|yesterday|episode|interview|guest|season|"
    r"talk|show|founder|engineer|builder|researcher|podcast)\b",
    re.I,
)

_FR_CHANNEL_WHITELIST = {
    "underscore_", "underscore", "génération ia", "generation ia", "generationia",
    "lecoinstat", "le coin stat", "comptoir ia", "comptoirai", "nico16184",
    "data driven 101", "scopeo", "trench tech", "trenchtech", "trenchtechoff",
    "tech café", "tech cafe", "thinkerview", "micode",
    "changement d'époque en cours", "changement depoque en cours",
    "journal du hacker", "la tech raconte",
    "paris ai", "paris.ai", "aitinkerers paris", "ai tinkerers paris",
    "france inter", "france info", "france culture", "rfi",
    "dataforgood", "data for good", "hugging face france",
}

_EN_CHANNEL_BLACKLIST = {
    "latent space", "no priors", "no priors podcast", "cognitive revolution",
    "mlops community", "mlops.community", "practical ai", "gradient dissent",
    "twiml ai podcast", "twiml", "the ai engineer", "ai engineer",
    "dwarkesh patel", "dwarkesh podcast", "lenny's podcast", "lenny's newsletter",
    "software engineering daily", "how i ai", "a16z", "a16z podcast",
    "sequoia training data", "training data", "ai daily brief", "weights & biases",
    "exponent", "the pragmatic engineer", "cbs mornings", "openai",
    "cleo abram", "greg isenberg", "rowan cheung",
}


def _normalize(name: str) -> str:
    return (name or "").strip().lower()


def is_french(episode: Dict) -> bool:
    channel = _normalize(episode.get("channel_title", ""))
    if any(w in channel for w in _FR_CHANNEL_WHITELIST):
        return True
    if any(b in channel for b in _EN_CHANNEL_BLACKLIST):
        return False

    title = episode.get("title", "") or ""
    desc = episode.get("description", "") or ""
    blob = f"{title} {desc}"

    if not blob.strip():
        return False

    has_accent = bool(_ACCENT_RE.search(blob))
    fr_hits = len(_FR_STOPWORDS.findall(blob))
    en_hits = len(_EN_STOPWORDS.findall(blob))

    # Strong signal: accents + at least a few FR stopwords → French
    if has_accent and fr_hits >= 2:
        return True

    # Dense FR stopwords and clearly more FR than EN
    if fr_hits >= 8 and fr_hits > en_hits * 1.5:
        return True

    # Accents alone in a short text — lean FR only if EN stopwords are rare
    if has_accent and en_hits <= 2:
        return True

    return False


def filter_french(episodes):
    return [ep for ep in episodes if is_french(ep)]

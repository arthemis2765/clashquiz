"""
Rate limiting léger, en mémoire, sans dépendance externe.

Suffisant pour un projet à un seul process (dev / petit déploiement). Si le projet
grandit avec plusieurs workers/serveurs, il faudra migrer vers une solution partagée
(Redis + slowapi par exemple), car ce compteur est local à chaque process.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict


def real_client_ip(headers, fallback: str) -> str:
    """Résout l'IP réelle du client derrière un proxy inverse (Railway, etc.).

    Railway (comme la plupart des PaaS) place l'app derrière un proxy : sans
    ça, `request.client.host` / `websocket.client.host` renvoie l'IP interne
    du proxy pour TOUTES les requêtes, ce qui rend le rate limiting par IP
    inutile (soit tout le monde partage le même compteur, soit la limite ne
    protège plus rien). Le proxy pose l'en-tête X-Forwarded-For avec la
    chaîne des IP traversées, la première étant celle du client d'origine.
    `headers` est un objet type Starlette Headers ou un dict compatible.
    """
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return fallback


class RateLimiter:
    # Toutes les N vérifications, on purge les clés dont plus aucun appel n'est
    # récent : sans ça, une clé (IP, joueur) créée une fois restait en mémoire
    # indéfiniment.
    _GC_EVERY = 500

    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._calls_since_gc = 0

    def _gc(self, now: float) -> None:
        for key in [
            k for k, hits in self._hits.items()
            if not hits or now - hits[-1] > self.period_seconds
        ]:
            del self._hits[key]

    def allow(self, key: str) -> bool:
        now = time.time()
        self._calls_since_gc += 1
        if self._calls_since_gc >= self._GC_EVERY:
            self._calls_since_gc = 0
            self._gc(now)
        hits = self._hits[key]
        while hits and now - hits[0] > self.period_seconds:
            hits.popleft()
        if len(hits) >= self.max_calls:
            return False
        hits.append(now)
        return True


# 10 inscriptions par heure et par IP : largement suffisant pour un usage normal,
# empêche un script de créer des milliers de comptes en boucle.
register_limiter = RateLimiter(max_calls=10, period_seconds=3600)

# 20 tentatives de code de partie privée par minute et par IP : un joueur qui se
# trompe de code a largement de quoi réessayer, mais ça bloque un bruteforce rapide.
private_join_limiter = RateLimiter(max_calls=20, period_seconds=60)

# 1 commentaire toutes les 30 secondes par joueur : laisse largement le temps
# d'écrire un avis, bloque le spam en boucle sur le mur public.
comment_limiter = RateLimiter(max_calls=1, period_seconds=30)

# 30 nouvelles parties solo toutes les 10 minutes par joueur : largement assez
# pour enchaîner les « Rejouer », mais bloque un script qui remplirait la table
# solo_runs de lignes vides.
solo_start_limiter = RateLimiter(max_calls=30, period_seconds=600)

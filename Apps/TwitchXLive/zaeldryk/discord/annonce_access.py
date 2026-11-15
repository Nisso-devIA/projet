"""Qui peut utiliser /annonce. Aucun appel Discord."""

OWNER_ID = 558595717610995712
ROLE_SENTINELLE_ID = 1541249715448848464  # ⚔️ Sentinelle
ROLE_OMBRE_ID = 1541249717516763177  # 🌑 Ombre
ANNOUNCE_ROLE_IDS = {ROLE_SENTINELLE_ID, ROLE_OMBRE_ID}


def can_use_annonce(user_id: int, role_ids) -> bool:
    if int(user_id) == OWNER_ID:
        return True
    return bool(ANNOUNCE_ROLE_IDS.intersection(int(role) for role in role_ids))

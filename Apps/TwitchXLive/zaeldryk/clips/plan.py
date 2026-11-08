"""Plan d'échantillonnage borné. Ne télécharge rien et n'ouvre aucun collecteur."""
from __future__ import annotations

from datetime import datetime, timedelta

MAX_BATCHES = 3
MAX_SAMPLE = timedelta(minutes=13, seconds=30)


def sample_plan(start: datetime, end: datetime) -> dict:
    if end <= start:
        raise ValueError("fenêtre vide")
    span = end - start
    batch = min(MAX_SAMPLE / MAX_BATCHES, span / MAX_BATCHES)
    slots = []
    cursor = start
    for index in range(MAX_BATCHES):
        stop = min(cursor + batch, end)
        if stop <= cursor:
            break
        slots.append(
            {
                "index": index + 1,
                "start": cursor.isoformat(),
                "end": stop.isoformat(),
                "seconds": int((stop - cursor).total_seconds()),
            }
        )
        cursor = stop
    total = sum(item["seconds"] for item in slots)
    cap = int(MAX_SAMPLE.total_seconds())
    if total > cap:
        raise RuntimeError("plan au-dessus du plafond")
    return {
        "batches": len(slots),
        "max_batches": MAX_BATCHES,
        "sampled_seconds": total,
        "cap_seconds": cap,
        "collector": "none",
        "slots": slots,
    }

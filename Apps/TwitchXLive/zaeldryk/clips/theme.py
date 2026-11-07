"""Thème musical explicite. Jamais une piste de remplacement non déclarée."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class WaitingMusic(Exception):
    """Le thème n'est pas fourni, ou sa licence n'est pas confirmée."""


@dataclass(frozen=True)
class Theme:
    theme_id: str
    path: Path | None
    license_verified: bool
    license_note: str

    def ready(self) -> bool:
        return bool(
            self.license_verified
            and self.path is not None
            and self.path.is_file()
            and self.path.stat().st_size > 0
        )

    def block_reason(self) -> str:
        if not self.license_verified:
            return (
                "attente musique : licence non vérifiée. "
                "Le thème du jeu n'est pas libre de droits tant qu'un ayant droit "
                "n'a pas autorisé ce fichier."
            )
        if self.path is None or not self.path.is_file() or self.path.stat().st_size == 0:
            return "attente musique : fichier de thème absent."
        return ""


def load_theme(config_path: Path) -> Theme:
    if not config_path.is_file():
        return Theme("", None, False, "fichier de thème absent")
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("clip-theme.json doit être un objet")
    rel = str(raw.get("file") or "").strip()
    path = None
    if rel:
        candidate = Path(rel)
        if not candidate.is_absolute():
            candidate = config_path.parent / candidate
        path = candidate
    note = str(raw.get("license_note") or "").strip()
    verified = raw.get("license_verified") is True
    return Theme(str(raw.get("theme_id") or "").strip(), path, verified, note)

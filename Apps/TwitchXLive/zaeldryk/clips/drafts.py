"""Brouillons liés au fichier, au salon et au texte. Jamais de publication ici."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

GUILD_ID = "867426693286461490"
CHANNEL_ID = "1541251088605519942"
TTL = timedelta(hours=24)


class DraftError(Exception):
    pass


class PublishDisabled(DraftError):
    pass


@dataclass
class Draft:
    draft_id: str
    sha256: str
    guild_id: str
    channel_id: str
    text: str
    status: str
    owner_id: str
    source_path: str
    output_path: str
    created_at: str
    expires_at: str
    message_id: str

    def expired(self, now: datetime) -> bool:
        exp = datetime.fromisoformat(self.expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now >= exp


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_text(text: str) -> str:
    if not text or not text.strip():
        raise DraftError("texte vide")
    lowered = text.lower()
    if "@everyone" in lowered or "@here" in lowered:
        raise DraftError("mention interdite")
    return text


def _check_destination(guild_id: str, channel_id: str) -> None:
    if guild_id != GUILD_ID or channel_id != CHANNEL_ID:
        raise DraftError("destination refusée")


class DraftStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
              draft_id TEXT PRIMARY KEY,
              sha256 TEXT NOT NULL,
              guild_id TEXT NOT NULL,
              channel_id TEXT NOT NULL,
              text TEXT NOT NULL,
              status TEXT NOT NULL,
              owner_id TEXT NOT NULL,
              source_path TEXT NOT NULL,
              output_path TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              message_id TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _row(self, row: sqlite3.Row | None) -> Draft | None:
        if row is None:
            return None
        return Draft(**{key: row[key] for key in row.keys()})

    def find_open(self, sha256: str, guild_id: str, channel_id: str, text: str) -> Draft | None:
        row = self.conn.execute(
            """
            SELECT * FROM drafts
            WHERE sha256=? AND guild_id=? AND channel_id=? AND text=?
              AND status IN ('awaiting_owner','waiting_music','approved','publishing','posted','needs_review')
            ORDER BY created_at DESC LIMIT 1
            """,
            (sha256, guild_id, channel_id, text),
        ).fetchone()
        return self._row(row)

    def import_file(
        self,
        source: Path,
        output: Path,
        text: str,
        *,
        status: str = "awaiting_owner",
        now: datetime | None = None,
    ) -> Draft:
        text = _check_text(text)
        _check_destination(GUILD_ID, CHANNEL_ID)
        digest = sha256_file(output if output.is_file() else source)
        existing = self.find_open(digest, GUILD_ID, CHANNEL_ID, text)
        if existing:
            return existing
        now = now or datetime.now(timezone.utc)
        draft_id = digest[:12] + "-" + uuid.uuid4().hex[:8]
        created = now.isoformat()
        expires = (now + TTL).isoformat()
        self.conn.execute(
            """
            INSERT INTO drafts (
              draft_id, sha256, guild_id, channel_id, text, status, owner_id,
              source_path, output_path, created_at, expires_at, message_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                draft_id,
                digest,
                GUILD_ID,
                CHANNEL_ID,
                text,
                status,
                "",
                str(source),
                str(output),
                created,
                expires,
                "",
            ),
        )
        self.conn.commit()
        got = self.get(draft_id)
        assert got is not None
        return got

    def get(self, draft_id: str) -> Draft | None:
        row = self.conn.execute(
            "SELECT * FROM drafts WHERE draft_id=?", (draft_id,)
        ).fetchone()
        return self._row(row)

    def expire_due(self, now: datetime) -> int:
        rows = self.conn.execute(
            """
            SELECT draft_id, expires_at FROM drafts
            WHERE status IN ('awaiting_owner','waiting_music','approved','publishing')
            """
        ).fetchall()
        n = 0
        for row in rows:
            draft = self.get(row["draft_id"])
            if draft and draft.expired(now):
                self._set(draft.draft_id, "expired")
                n += 1
        return n

    def _set(self, draft_id: str, status: str, **extra: str) -> Draft:
        sets = ["status=?"]
        values: list[str] = [status]
        for key, value in extra.items():
            sets.append(f"{key}=?")
            values.append(value)
        values.append(draft_id)
        self.conn.execute(
            f"UPDATE drafts SET {', '.join(sets)} WHERE draft_id=?", values
        )
        self.conn.commit()
        got = self.get(draft_id)
        assert got is not None
        return got

    def decide(
        self,
        draft_id: str,
        *,
        actor_is_owner: bool,
        actor_id: str,
        sha256: str,
        text: str,
        guild_id: str,
        channel_id: str,
        approve: bool,
        now: datetime | None = None,
    ) -> Draft:
        draft = self.get(draft_id)
        if draft is None:
            raise DraftError("brouillon inconnu")
        now = now or datetime.now(timezone.utc)
        if draft.expired(now) or draft.status == "expired":
            return self._set(draft.draft_id, "expired")
        if draft.status in {"rejected", "posted"}:
            return draft
        if draft.status == "waiting_music":
            raise DraftError("attente musique, rien n'est envoyé")
        if not actor_is_owner:
            raise DraftError("réservé au propriétaire du serveur")
        if (
            draft.sha256 != sha256
            or draft.text != text
            or draft.guild_id != guild_id
            or draft.channel_id != channel_id
        ):
            raise DraftError("fichier, texte ou destination ne correspondent pas")
        if not approve:
            return self._set(draft.draft_id, "rejected", owner_id=actor_id)
        return self._set(draft.draft_id, "approved", owner_id=actor_id)

    def publish(self, draft_id: str, transport, *, enabled: bool, now: datetime | None = None) -> Draft:
        """Envoie seulement si enabled et si le brouillon est approuvé. Sinon ne poste pas."""
        draft = self.get(draft_id)
        if draft is None:
            raise DraftError("brouillon inconnu")
        now = now or datetime.now(timezone.utc)
        if not enabled:
            raise PublishDisabled("publication désactivée")
        if draft.status != "approved":
            raise DraftError(f"statut {draft.status}, rien n'est envoyé")
        if draft.expired(now):
            self._set(draft.draft_id, "expired")
            raise DraftError("expiré, rien n'est envoyé")
        if draft.message_id:
            return draft
        self._set(draft.draft_id, "publishing")
        try:
            message_id = transport(
                guild_id=draft.guild_id,
                channel_id=draft.channel_id,
                text=draft.text,
                path=draft.output_path,
                sha256=draft.sha256,
            )
        except Exception:
            self._set(draft.draft_id, "needs_review")
            raise
        if not message_id:
            self._set(draft.draft_id, "needs_review")
            raise DraftError("envoi sans identifiant, rien n'est marqué publié")
        return self._set(draft.draft_id, "posted", message_id=str(message_id))


def dumps_public(draft: Draft) -> str:
    """Résumé sans chemin secret ni jeton."""
    return json.dumps(
        {
            "draft_id": draft.draft_id,
            "sha256": draft.sha256,
            "guild_id": draft.guild_id,
            "channel_id": draft.channel_id,
            "text": draft.text,
            "status": draft.status,
        },
        ensure_ascii=False,
    )

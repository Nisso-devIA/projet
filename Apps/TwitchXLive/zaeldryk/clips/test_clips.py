#!/usr/bin/env python3
"""Tests locaux. Aucun appel Discord ni YouTube."""
from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "youtube-clips"))

from clips.drafts import DraftError, DraftStore, PublishDisabled  # noqa: E402
from clips.encode import (  # noqa: E402
    DISCORD_LIMIT,
    ffmpeg_cmd,
    video_budget,
    ClipTooLong,
    encode_draft,
)
from clips.permissions import missing_permissions, REQUIRED  # noqa: E402
from clips.plan import sample_plan, MAX_BATCHES  # noqa: E402
from clips.theme import Theme, WaitingMusic, load_theme  # noqa: E402
from config import Settings  # noqa: E402


class PauseTests(unittest.TestCase):
    def test_upload_defaults_off(self):
        settings = Settings({})
        self.assertFalse(settings.upload_enabled)

    def test_upload_explicit_on(self):
        settings = Settings({"YOUTUBE_CLIPS_UPLOAD": "1"})
        self.assertTrue(settings.upload_enabled)


class ThemeTests(unittest.TestCase):
    def test_missing_file_waits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clip-theme.json"
            path.write_text(
                '{"theme_id":"oot","file":"missing.wav","license_verified":false,'
                '"license_note":"pas libre"}',
                encoding="utf-8",
            )
            theme = load_theme(path)
            self.assertFalse(theme.ready())
            self.assertIn("licence", theme.block_reason())
            with self.assertRaises(WaitingMusic):
                encode_draft(Path(tmp) / "in.mp4", theme, Path(tmp) / "out.mp4")


class EncodeCommandTests(unittest.TestCase):
    def test_budget_refuses_long_clip(self):
        with self.assertRaises(ClipTooLong):
            video_budget(30 * 60)

    def test_command_drops_source_audio(self):
        cmd = ffmpeg_cmd(
            Path("source.mp4"),
            Path("theme.wav"),
            Path("out.mp4"),
            12,
            400_000,
        )
        self.assertNotIn("0:a", cmd)
        self.assertIn("[a]", cmd)
        self.assertIn("720:1280", "".join(cmd))
        self.assertLess(video_budget(20), 4_000_000)


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = DraftStore(Path(self.tmp.name) / "drafts.sqlite")
        self.src = Path(self.tmp.name) / "clip.mp4"
        self.src.write_bytes(b"video-bytes")
        self.now = datetime(2026, 11, 7, 18, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_dedupe_and_owner_gate(self):
        first = self.store.import_file(self.src, self.src, "Live 22h30", now=self.now)
        second = self.store.import_file(self.src, self.src, "Live 22h30", now=self.now)
        self.assertEqual(first.draft_id, second.draft_id)
        with self.assertRaises(DraftError):
            self.store.decide(
                first.draft_id,
                actor_is_owner=False,
                actor_id="9",
                sha256=first.sha256,
                text=first.text,
                guild_id=first.guild_id,
                channel_id=first.channel_id,
                approve=True,
                now=self.now,
            )
        approved = self.store.decide(
            first.draft_id,
            actor_is_owner=True,
            actor_id="1",
            sha256=first.sha256,
            text=first.text,
            guild_id=first.guild_id,
            channel_id=first.channel_id,
            approve=True,
            now=self.now,
        )
        self.assertEqual(approved.status, "approved")

    def test_mismatch_reject_expire_never_call_transport(self):
        draft = self.store.import_file(self.src, self.src, "texte exact", now=self.now)
        calls = []

        def transport(**kwargs):
            calls.append(kwargs)
            return "999"

        with self.assertRaises(DraftError):
            self.store.decide(
                draft.draft_id,
                actor_is_owner=True,
                actor_id="1",
                sha256="0" * 64,
                text=draft.text,
                guild_id=draft.guild_id,
                channel_id=draft.channel_id,
                approve=True,
                now=self.now,
            )
        with self.assertRaises(PublishDisabled):
            self.store.publish(draft.draft_id, transport, enabled=False, now=self.now)
        self.assertEqual(calls, [])
        refused = self.store.decide(
            draft.draft_id,
            actor_is_owner=True,
            actor_id="1",
            sha256=draft.sha256,
            text=draft.text,
            guild_id=draft.guild_id,
            channel_id=draft.channel_id,
            approve=False,
            now=self.now,
        )
        self.assertEqual(refused.status, "rejected")
        with self.assertRaises(DraftError):
            self.store.publish(draft.draft_id, transport, enabled=True, now=self.now)
        self.assertEqual(calls, [])

        other = self.store.import_file(self.src, self.src, "autre texte", now=self.now)
        expired = self.store.decide(
            other.draft_id,
            actor_is_owner=True,
            actor_id="1",
            sha256=other.sha256,
            text=other.text,
            guild_id=other.guild_id,
            channel_id=other.channel_id,
            approve=True,
            now=self.now + timedelta(hours=25),
        )
        self.assertEqual(expired.status, "expired")
        with self.assertRaises(DraftError):
            self.store.publish(other.draft_id, transport, enabled=True, now=self.now + timedelta(hours=25))
        self.assertEqual(calls, [])

    def test_waiting_music_cannot_be_approved(self):
        draft = self.store.import_file(
            self.src, self.src, "en attente", status="waiting_music", now=self.now
        )
        with self.assertRaises(DraftError):
            self.store.decide(
                draft.draft_id,
                actor_is_owner=True,
                actor_id="1",
                sha256=draft.sha256,
                text=draft.text,
                guild_id=draft.guild_id,
                channel_id=draft.channel_id,
                approve=True,
                now=self.now,
            )

    def test_publish_failure_does_not_mark_posted(self):
        draft = self.store.import_file(self.src, self.src, "reprise", now=self.now)
        self.store.decide(
            draft.draft_id,
            actor_is_owner=True,
            actor_id="1",
            sha256=draft.sha256,
            text=draft.text,
            guild_id=draft.guild_id,
            channel_id=draft.channel_id,
            approve=True,
            now=self.now,
        )

        def boom(**kwargs):
            raise RuntimeError("coupure")

        with self.assertRaises(RuntimeError):
            self.store.publish(draft.draft_id, boom, enabled=True, now=self.now)
        kept = self.store.get(draft.draft_id)
        self.assertEqual(kept.status, "needs_review")
        self.assertEqual(kept.message_id, "")

    def test_everyone_rejected(self):
        with self.assertRaises(DraftError):
            self.store.import_file(self.src, self.src, "salut @everyone", now=self.now)


class PlanTests(unittest.TestCase):
    def test_tonight_window_stays_bounded(self):
        start = datetime(2026, 11, 7, 21, 30, tzinfo=timezone.utc)
        end = datetime(2026, 11, 8, 0, 30, tzinfo=timezone.utc)
        plan = sample_plan(start, end)
        self.assertLessEqual(plan["batches"], MAX_BATCHES)
        self.assertLessEqual(plan["sampled_seconds"], 13 * 60 + 30)
        self.assertEqual(plan["collector"], "none")


class PermissionTests(unittest.TestCase):
    def test_missing_attach(self):
        granted = REQUIRED["view_channel"] | REQUIRED["send_messages"]
        missing = missing_permissions(granted)
        self.assertIn("attach_files", missing)


class FfmpegTests(unittest.TestCase):
    def test_real_encode_replaces_audio_and_stays_small(self):
        ffmpeg = __import__("shutil").which("ffmpeg")
        if not ffmpeg:
            self.skipTest("ffmpeg absent")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.mp4"
            theme_path = tmp_path / "theme.wav"
            out = tmp_path / "draft.mp4"
            subprocess = __import__("subprocess")
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "testsrc=size=320x180:rate=15:duration=2",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-c:v", "libx264", "-c:a", "aac", "-shortest", str(source),
                ],
                check=True,
                capture_output=True,
            )
            with wave.open(str(theme_path), "w") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b"\x10\x00" * 8000)
            theme = Theme("test", theme_path, True, "fichier de test, pas une bande originale")
            encode_draft(source, theme, out)
            self.assertLess(out.stat().st_size, DISCORD_LIMIT)
            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=p=0:s=x",
                    str(out),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(probe.stdout.strip(), "720x1280")
            audio = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-select_streams", "a",
                    "-show_entries", "stream=codec_type",
                    "-of", "csv=p=0",
                    str(out),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("audio", audio.stdout)


if __name__ == "__main__":
    unittest.main()

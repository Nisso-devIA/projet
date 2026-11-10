#!/usr/bin/env python3
"""Captcha charset, attempt limits, and PNG generation. No Discord calls."""

from __future__ import annotations

import io
import unittest
import unittest.mock

from PIL import Image

from captcha_image import (
    AMBIGUOUS,
    CHARSET,
    CODE_LENGTH,
    COOLDOWN_SECONDS,
    MAX_ATTEMPTS,
    TTL_SECONDS,
    CaptchaGate,
    CooldownError,
    codes_match,
    render_captcha_png,
)


class MatchTests(unittest.TestCase):
    def test_case_and_surrounding_space_match(self):
        self.assertTrue(codes_match("  ab23k ", "AB23K"))
        self.assertFalse(codes_match("AB23K!", "AB23K"))

    def test_charset_has_no_ambiguous_glyphs(self):
        self.assertTrue(set(CHARSET).isdisjoint(AMBIGUOUS))
        self.assertNotIn("0", CHARSET)
        self.assertNotIn("O", CHARSET)
        self.assertNotIn("1", CHARSET)
        self.assertNotIn("I", CHARSET)
        self.assertNotIn("l", CHARSET)


class GateTests(unittest.TestCase):
    def test_issue_uses_six_unambiguous_characters(self):
        gate = CaptchaGate()
        session = gate.issue(7, now=1_000.0)
        self.assertEqual(len(session.code), CODE_LENGTH)
        self.assertTrue(set(session.code) <= set(CHARSET))
        self.assertEqual(session.expires_at, 1_000.0 + TTL_SECONDS)
        self.assertEqual(session.attempts, 0)

    def test_success_is_case_insensitive_and_clears_the_session(self):
        gate = CaptchaGate()
        session = gate.issue(7, now=1_000.0)
        result = gate.submit(7, session.captcha_id, session.code.lower(), now=1_010.0)
        self.assertEqual(result.status, "ok")
        self.assertNotIn(7, gate.sessions)

    def test_three_failures_lock_for_two_minutes(self):
        gate = CaptchaGate()
        session = gate.issue(7, now=1_000.0)
        first = gate.submit(7, session.captcha_id, "ZZZZZZ", now=1_001.0)
        second = gate.submit(7, session.captcha_id, "YYYYYY", now=1_002.0)
        third = gate.submit(7, session.captcha_id, "XXXXXX", now=1_003.0)
        self.assertEqual(first.status, "wrong")
        self.assertEqual(first.left, 2)
        self.assertEqual(second.left, 1)
        self.assertEqual(third.status, "locked")
        self.assertEqual(third.attempts, MAX_ATTEMPTS)
        self.assertEqual(third.retry_after, COOLDOWN_SECONDS)
        with self.assertRaises(CooldownError) as caught:
            gate.issue(7, now=1_010.0)
        self.assertAlmostEqual(caught.exception.retry_after, 113.0)
        fresh = gate.issue(7, now=1_003.0 + COOLDOWN_SECONDS)
        self.assertNotEqual(fresh.captcha_id, session.captcha_id)

    def test_new_captcha_resets_attempts(self):
        gate = CaptchaGate()
        session = gate.issue(7, now=1_000.0)
        gate.submit(7, session.captcha_id, "NOPE", now=1_001.0)
        replacement = gate.issue(7, now=1_002.0)
        result = gate.submit(7, session.captcha_id, session.code, now=1_003.0)
        self.assertEqual(result.status, "stale")
        ok = gate.submit(7, replacement.captcha_id, replacement.code, now=1_004.0)
        self.assertEqual(ok.status, "ok")
        self.assertEqual(ok.attempts, 1)

    def test_expired_captcha_is_rejected(self):
        gate = CaptchaGate()
        session = gate.issue(7, now=1_000.0)
        result = gate.submit(7, session.captcha_id, session.code, now=1_000.0 + TTL_SECONDS)
        self.assertEqual(result.status, "expired")
        self.assertNotIn(7, gate.sessions)


class ImageTests(unittest.TestCase):
    def test_png_is_a_real_noisy_image(self):
        png = render_captcha_png("ZAEL7K")
        self.assertTrue(png.startswith(b"\x89PNG"))
        image = Image.open(io.BytesIO(png))
        self.assertEqual(image.size, (380, 140))
        colors = image.getcolors(maxcolors=image.size[0] * image.size[1])
        self.assertGreater(len(colors), 30)

    def test_renderer_rejects_ambiguous_code(self):
        with self.assertRaises(ValueError):
            render_captcha_png("O0I1lA")


class SecretTests(unittest.TestCase):
    def test_codes_come_from_the_charset(self):
        gate = CaptchaGate()
        with unittest.mock.patch("captcha_image.secrets.choice", side_effect=list("H3NK4P")):
            session = gate.issue(1, now=0)
        self.assertEqual(session.code, "H3NK4P")


if __name__ == "__main__":
    unittest.main()

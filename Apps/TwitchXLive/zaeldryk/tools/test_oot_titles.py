#!/usr/bin/env python3
"""Les titres de live gardent de vrais emojis Unicode."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oot_titles import (  # noqa: E402
    OOT_TITLES,
    SHORTCODE,
    TITLE_LIMIT,
    encode_channel_body,
    has_unicode_emoji,
)


class TitleEmojiTests(unittest.TestCase):
    def test_titles_use_unicode_emoji_not_shortcodes(self):
        self.assertGreaterEqual(len(OOT_TITLES), 1)
        for title in OOT_TITLES:
            self.assertTrue(has_unicode_emoji(title), title)
            self.assertIsNone(SHORTCODE.search(title), title)
            self.assertLessEqual(len(title), TITLE_LIMIT, title)
            low = title.lower()
            self.assertNotIn("remake", low)
            self.assertNotIn("switch", low)

    def test_json_utf8_roundtrip_keeps_the_character(self):
        title = OOT_TITLES[0]
        raw = encode_channel_body({"title": title})
        self.assertIn("🧚".encode("utf-8"), raw)
        self.assertIn("😉".encode("utf-8"), raw)
        self.assertNotIn(b"\\u", raw)
        loaded = json.loads(raw.decode("utf-8"))
        self.assertEqual(loaded["title"], title)


if __name__ == "__main__":
    unittest.main()

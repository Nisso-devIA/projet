#!/usr/bin/env python3
"""Importe un clip local. N'envoie rien sur Discord ni YouTube."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ZAEL_ROOT = Path(__file__).resolve().parents[1]
if str(ZAEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ZAEL_ROOT))

from clips.drafts import DraftStore, dumps_public  # noqa: E402
from clips.encode import encode_draft  # noqa: E402
from clips.theme import load_theme  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Importe un clip sans le publier")
    parser.add_argument("--file", required=True)
    parser.add_argument("--text", required=True)
    args = parser.parse_args()
    source = Path(args.file)
    theme = load_theme(ZAEL_ROOT / "config" / "clip-theme.json")
    store = DraftStore(ZAEL_ROOT / "state" / "clip-drafts.sqlite")
    try:
        if not theme.ready():
            draft = store.import_file(
                source, source, args.text, status="waiting_music"
            )
            print(dumps_public(draft))
            print(theme.block_reason())
            return 2
        out_dir = ZAEL_ROOT / "state" / "clip-out"
        out = out_dir / (source.stem + "-draft.mp4")
        encode_draft(source, theme, out)
        draft = store.import_file(source, out, args.text)
        print(dumps_public(draft))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())

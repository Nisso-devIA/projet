"""Droits minimaux pour déposer une vidéo dans un salon, sans autre pouvoir."""

VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
EMBED_LINKS = 1 << 14
ATTACH_FILES = 1 << 15
READ_MESSAGE_HISTORY = 1 << 16

REQUIRED = {
    "view_channel": VIEW_CHANNEL,
    "send_messages": SEND_MESSAGES,
    "embed_links": EMBED_LINKS,
    "attach_files": ATTACH_FILES,
    "read_message_history": READ_MESSAGE_HISTORY,
}


def missing_permissions(granted: int) -> list[str]:
    return [name for name, bit in REQUIRED.items() if granted & bit == 0]

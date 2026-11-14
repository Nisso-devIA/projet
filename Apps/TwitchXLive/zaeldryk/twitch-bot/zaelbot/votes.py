"""Paris et sondages. Helix si le jeton broadcaster passe, sinon un vote dans le chat."""

from __future__ import annotations

from dataclasses import dataclass, field


def api_available(status: int) -> bool:
    return status in {200, 202}


@dataclass
class VoteSpec:
    title: str
    choices: list[str]
    seconds: int


@dataclass
class OpenVote:
    kind: str
    title: str
    choices: list[str]
    ends_at: float
    mode: str
    remote_id: str = ""
    outcome_ids: list[str] = field(default_factory=list)
    ballots: dict[str, int] = field(default_factory=dict)

    def cast(self, user: str, text: str, now: float) -> bool:
        if self.mode != "chat" or now > self.ends_at:
            return False
        index = choice_index(text, self.choices)
        if index is None:
            return False
        self.ballots[user.lower()] = index
        return True

    def tally(self) -> list[int]:
        totals = [0 for _ in self.choices]
        for index in self.ballots.values():
            if 0 <= index < len(totals):
                totals[index] += 1
        return totals


class VoteBook:
    def __init__(self) -> None:
        self.current: OpenVote | None = None

    def open_chat(self, kind: str, spec: VoteSpec, now: float) -> str:
        self.current = OpenVote(
            kind=kind,
            title=spec.title,
            choices=list(spec.choices),
            ends_at=now + spec.seconds,
            mode="chat",
        )
        return chat_prompt(kind, spec)

    def open_remote(self, kind: str, spec: VoteSpec, now: float, remote_id: str, outcome_ids: list[str]) -> None:
        self.current = OpenVote(
            kind=kind,
            title=spec.title,
            choices=list(spec.choices),
            ends_at=now + spec.seconds,
            mode="helix",
            remote_id=remote_id,
            outcome_ids=list(outcome_ids),
        )

    def cast(self, user: str, text: str, now: float) -> bool:
        if self.current is None:
            return False
        return self.current.cast(user, text, now)

    def close(self) -> OpenVote | None:
        current = self.current
        self.current = None
        return current


def choice_index(text: str, choices: list[str]) -> int | None:
    clean = " ".join((text or "").split()).casefold()
    if not clean or clean.startswith("!"):
        return None
    if clean.isdigit():
        number = int(clean)
        if 1 <= number <= len(choices):
            return number - 1
        return None
    for index, choice in enumerate(choices):
        if clean == choice.casefold():
            return index
    return None


def chat_prompt(kind: str, spec: VoteSpec) -> str:
    label = "Pari" if kind == "pari" else "Sondage"
    options = " | ".join(f"{index}. {choice}" for index, choice in enumerate(spec.choices, start=1))
    return f"{label} dans le chat ({spec.seconds}s) : {spec.title}. {options}. Tape le numéro."


def tally_text(vote: OpenVote) -> str:
    parts = [f"{choice} {count}" for choice, count in zip(vote.choices, vote.tally())]
    return f"Résultat : {vote.title}. " + ", ".join(parts) + "."


def parse_vote_args(args: str, *, default_seconds: int = 120) -> dict:
    text = " ".join((args or "").split())
    if not text:
        return {"action": "error", "message": 'Usage : !pari "Question ?" Oui | Non 120'}
    lowered = text.casefold()
    if lowered in {"annule", "cancel"}:
        return {"action": "cancel"}
    if lowered == "fin" or lowered.startswith("fin "):
        rest = text[3:].strip()
        if not rest:
            return {"action": "finish", "index": None}
        if rest.isdigit() and int(rest) >= 1:
            return {"action": "finish", "index": int(rest)}
        return {"action": "error", "message": "Usage : !pari fin 1"}
    title, rest = _split_title(text)
    if not title:
        return {"action": "error", "message": 'Précise la question entre guillemets. Exemple : !pari "Boss battu ?" Oui | Non 120'}
    pieces = [piece.strip() for piece in rest.split("|")]
    seconds = default_seconds
    if pieces and pieces[-1].isdigit():
        seconds = int(pieces.pop())
    elif pieces:
        head, _, tail = pieces[-1].rpartition(" ")
        if tail.isdigit() and head.strip():
            seconds = int(tail)
            pieces[-1] = head.strip()
    choices = [piece for piece in pieces if piece]
    if len(choices) < 2:
        return {"action": "error", "message": "Il faut au moins deux choix, séparés par |."}
    if len(choices) > 10:
        return {"action": "error", "message": "Dix choix maximum."}
    return {"action": "start", "spec": VoteSpec(title=title[:60], choices=choices, seconds=seconds)}


def _split_title(text: str) -> tuple[str, str]:
    if len(text) >= 2 and text[0] in {'"', "«"}:
        closing = "»" if text[0] == "«" else '"'
        end = text.find(closing, 1)
        if end > 1:
            return text[1:end].strip(), text[end + 1 :].strip()
    return "", ""


def prediction_body(broadcaster_id: str, spec: VoteSpec) -> dict:
    window = max(30, min(1800, int(spec.seconds)))
    return {
        "broadcaster_id": broadcaster_id,
        "title": spec.title[:45],
        "outcomes": [{"title": choice[:25]} for choice in spec.choices[:10]],
        "prediction_window": window,
    }


def prediction_end_body(broadcaster_id: str, prediction_id: str, outcome_id: str | None) -> dict:
    if outcome_id:
        return {
            "broadcaster_id": broadcaster_id,
            "id": prediction_id,
            "status": "RESOLVED",
            "winning_outcome_id": outcome_id,
        }
    return {"broadcaster_id": broadcaster_id, "id": prediction_id, "status": "CANCELED"}


def poll_body(broadcaster_id: str, spec: VoteSpec) -> dict:
    duration = max(15, min(1800, int(spec.seconds)))
    return {
        "broadcaster_id": broadcaster_id,
        "title": spec.title[:60],
        "choices": [{"title": choice[:25]} for choice in spec.choices[:5]],
        "duration": duration,
    }


def poll_end_body(broadcaster_id: str, poll_id: str, *, cancel: bool) -> dict:
    return {
        "broadcaster_id": broadcaster_id,
        "id": poll_id,
        "status": "ARCHIVED" if cancel else "TERMINATED",
    }

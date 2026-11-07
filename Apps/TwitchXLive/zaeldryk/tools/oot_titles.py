"""Titres Twitch pour Zelda Ocarina of Time Remake sur Switch 2."""
from __future__ import annotations

import unicodedata

OOT_KEYS = ("ocarina", "oot", "zelda")
OOT_QUERY = "The Legend of Zelda: Ocarina of Time"

# Pas de mot qui ferait passer le live pour une fin (offline, ending, brb, fin de live).
OOT_TITLES = [
    "Zelda Ocarina of Time Remake sur Switch 2 — on entre dans Hyrule",
    "Ocarina of Time Remake Switch 2 : le premier temple, en direct",
    "Hyrule t'attend — Zelda OOT Remake sur Switch 2, sans spoiler",
    "Switch 2 : Ocarina of Time Remake, je me perds et vous guidez",
    "La musique d'Hyrule — Zelda Ocarina of Time Remake Switch 2",
    "Viens voir le remake — Ocarina of Time sur Switch 2, chat ouvert",
    "Ocarina of Time Remake Switch 2 : on avance, on crie, on recommence",
    "Première découverte — Zelda OOT Remake sur Switch 2",
]

# Noms les plus longs d'abord : « temple de l'eau » doit gagner sur « temple ».
OOT_PLACES = [
    {
        "id": "eau",
        "label": "Temple de l'eau",
        "names": ("temple de l'eau", "temple de leau", "water temple"),
        "titles": (
            "Temple de l'eau — Zelda Ocarina of Time Remake Switch 2",
            "On se noie au Temple de l'eau — Ocarina of Time Remake Switch 2",
        ),
    },
    {
        "id": "ombre",
        "label": "Temple de l'ombre",
        "names": ("temple de l'ombre", "temple de lombre", "shadow temple"),
        "titles": (
            "Temple de l'ombre — Zelda Ocarina of Time Remake Switch 2",
            "Sous le cimetière : Temple de l'ombre, OOT Remake Switch 2",
        ),
    },
    {
        "id": "esprit",
        "label": "Temple de l'esprit",
        "names": ("temple de l'esprit", "temple de lesprit", "spirit temple"),
        "titles": (
            "Temple de l'esprit — Zelda Ocarina of Time Remake Switch 2",
            "Désert et miroirs : Temple de l'esprit, OOT Remake Switch 2",
        ),
    },
    {
        "id": "foret",
        "label": "Temple de la forêt",
        "names": ("temple de la foret", "forest temple"),
        "titles": (
            "Temple de la forêt — Zelda Ocarina of Time Remake Switch 2",
            "Couloirs et tableaux : Temple de la forêt, OOT Remake Switch 2",
        ),
    },
    {
        "id": "feu",
        "label": "Temple du feu",
        "names": ("temple du feu", "fire temple"),
        "titles": (
            "Temple du feu — Zelda Ocarina of Time Remake Switch 2",
            "Lave et marteaux : Temple du feu, OOT Remake Switch 2",
        ),
    },
    {
        "id": "ganon",
        "label": "Château de Ganon",
        "names": ("chateau de ganon", "ganon", "ganondorf"),
        "titles": (
            "Château de Ganon — Zelda Ocarina of Time Remake Switch 2",
            "Dernière ligne : Ganon, Ocarina of Time Remake Switch 2",
        ),
    },
    {
        "id": "kokiri",
        "label": "Forêt Kokiri",
        "names": ("kokiri", "cocorico", "arbre mojo", "deku"),
        "titles": (
            "Forêt Kokiri — Zelda Ocarina of Time Remake Switch 2",
            "Arbre Mojo : le début d'Hyrule, OOT Remake Switch 2",
        ),
    },
    {
        "id": "plaine",
        "label": "Plaine d'Hyrule",
        "names": ("plaine", "hyrule field"),
        "titles": (
            "Plaine d'Hyrule — Zelda Ocarina of Time Remake Switch 2",
            "À cheval dans la Plaine d'Hyrule, OOT Remake Switch 2",
        ),
    },
    {
        "id": "chateau",
        "label": "Château d'Hyrule",
        "names": ("chateau d'hyrule", "chateau dhyrule", "hyrule castle", "bourg"),
        "titles": (
            "Château d'Hyrule — Zelda Ocarina of Time Remake Switch 2",
            "Bourg et château : Zelda OOT Remake sur Switch 2",
        ),
    },
    {
        "id": "ranch",
        "label": "Ranch Lon Lon",
        "names": ("lon lon", "ranch"),
        "titles": (
            "Ranch Lon Lon — Zelda Ocarina of Time Remake Switch 2",
            "Epona nous attend au Ranch Lon Lon, OOT Remake Switch 2",
        ),
    },
    {
        "id": "kakariko",
        "label": "Village Cocorico",
        "names": ("kakariko", "cocorico village"),
        "titles": (
            "Village Cocorico — Zelda Ocarina of Time Remake Switch 2",
            "Kakariko la nuit : Ocarina of Time Remake Switch 2",
        ),
    },
    {
        "id": "peril",
        "label": "Mont du Péril",
        "names": ("mont du peril", "death mountain", "dodongo"),
        "titles": (
            "Mont du Péril — Zelda Ocarina of Time Remake Switch 2",
            "Caverne Dodongo : Ocarina of Time Remake Switch 2",
        ),
    },
    {
        "id": "zora",
        "label": "Domaine Zora",
        "names": ("zora", "jabu"),
        "titles": (
            "Domaine Zora — Zelda Ocarina of Time Remake Switch 2",
            "Dans Jabu-Jabu : Ocarina of Time Remake Switch 2",
        ),
    },
    {
        "id": "hylia",
        "label": "Lac Hylia",
        "names": ("hylia", "lac"),
        "titles": (
            "Lac Hylia — Zelda Ocarina of Time Remake Switch 2",
            "Au fond du Lac Hylia : OOT Remake Switch 2",
        ),
    },
    {
        "id": "gerudo",
        "label": "Désert Gerudo",
        "names": ("gerudo", "desert"),
        "titles": (
            "Désert Gerudo — Zelda Ocarina of Time Remake Switch 2",
            "Vallée Gerudo : Ocarina of Time Remake Switch 2",
        ),
    },
    {
        "id": "perdus",
        "label": "Bois perdus",
        "names": ("bois perdus", "lost woods"),
        "titles": (
            "Bois perdus — Zelda Ocarina of Time Remake Switch 2",
            "On tourne en rond dans les Bois perdus, OOT Remake Switch 2",
        ),
    },
]


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.lower())
    plain = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")
    return plain.replace("’", "'")


def detect_place(text: str) -> dict | None:
    blob = _norm(text or "")
    found: tuple[int, dict] | None = None
    for place in OOT_PLACES:
        for name in place["names"]:
            if name in blob and (found is None or len(name) > found[0]):
                found = (len(name), place)
    return found[1] if found else None


def titles_for(place: dict | None, raw: str = "") -> list[str]:
    if place:
        return list(place["titles"])
    cleaned = " ".join((raw or "").split())
    if cleaned:
        return [
            f"{cleaned} — Zelda Ocarina of Time Remake Switch 2"[:140],
            f"On est à {cleaned} — Ocarina of Time Remake Switch 2"[:140],
        ]
    return list(OOT_TITLES)

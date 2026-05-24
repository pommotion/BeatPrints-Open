"""Shared API logic for local and serverless web entrypoints."""

from __future__ import annotations

import json
import tempfile
import time

from dataclasses import asdict
from pathlib import Path

from BeatPrints import errors, lyrics, poster, spotify


SPOTIFY = spotify.Spotify()
LYRICS = lyrics.Lyrics()
THEMES = ["Light", "Dark", "Catppuccin", "Gruvbox", "Nord", "RosePine", "Everforest"]


def json_default(value):
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def dumps_json(payload: dict) -> bytes:
    return json.dumps(payload, default=json_default).encode("utf-8")


def metadata_from_payload(payload: dict) -> spotify.TrackMetadata:
    required = ["name", "artist", "album", "released", "duration", "image", "label", "id"]
    data = {key: str(payload.get(key, "")) for key in required}
    return spotify.TrackMetadata(**data)


def line_range(lines: list[str], start: int, end: int) -> str:
    cleaned = [line for line in lines if line.strip()]
    if len(cleaned) < 4:
        return "\n".join(cleaned)

    start = max(start, 1)
    end = min(end, len(cleaned))
    selected = cleaned[start - 1 : end]
    if len(selected) != 4:
        selected = cleaned[:4]
    return "\n".join(selected)


def latest_created_in(directory: Path, before: set[Path]) -> Path | None:
    after = set(directory.glob("*.png"))
    created = after - before
    if not created:
        return None
    return max(created, key=lambda path: path.stat().st_mtime)


def search_metadata(query: str, kind: str = "track", limit: int = 6) -> dict:
    if not query:
        raise ValueError("Search query is required.")

    try:
        if kind == "album":
            results = SPOTIFY.get_album(query, limit=limit)
        else:
            results = SPOTIFY.get_track(query, limit=limit)
    except (errors.NoMatchingTrackFound, errors.NoMatchingAlbumFound):
        results = []

    return {"results": results}


def lyrics_for_track(track_payload: dict) -> dict:
    track = metadata_from_payload(track_payload)

    try:
        text, source = LYRICS.get_lyrics_with_source(track)
    except errors.NoLyricsAvailable:
        return {
            "lyrics": "",
            "lines": [],
            "source": "",
            "warning": "No lyrics found. Enter custom lyrics to generate a poster.",
        }

    lines = [line for line in text.splitlines() if line.strip()]
    return {"lyrics": text, "lines": lines, "source": source}


def generate_poster_png(payload: dict) -> tuple[bytes, str]:
    track = metadata_from_payload(payload.get("track", {}))
    theme = payload.get("theme", "Light")
    accent = bool(payload.get("accent", False))
    custom_lyrics = str(payload.get("customLyrics", "")).strip()
    lines = payload.get("lines") or []
    start = int(payload.get("start", 1))
    end = int(payload.get("end", 4))

    if theme not in THEMES:
        raise ValueError("Invalid theme.")

    selected = custom_lyrics or line_range(lines, start, end)
    if not selected:
        raise ValueError("Select lyrics or enter custom lyrics.")

    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp_dir:
        temp_output = Path(temp_dir)
        before = set(temp_output.glob("*.png"))
        poster.Poster(str(temp_output)).track(track, selected, accent=accent, theme=theme)

        time.sleep(0.05)
        created = latest_created_in(temp_output, before)
        if created is None:
            raise RuntimeError("Poster was generated but no output file was found.")

        return created.read_bytes(), created.name

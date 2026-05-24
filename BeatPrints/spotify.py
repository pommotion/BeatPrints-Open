"""
Module: spotify.py

Provides Spotify-compatible metadata classes backed by open catalog APIs.
"""

import datetime
import random
import requests

from dataclasses import dataclass
from typing import Any, List
from urllib.parse import quote_plus

from BeatPrints.errors import (
    InvalidSearchLimit,
    NoMatchingAlbumFound,
    NoMatchingTrackFound,
)


ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"
DEEZER_TRACK_SEARCH_URL = "https://api.deezer.com/search/track"
REQUEST_TIMEOUT = 20


@dataclass
class TrackMetadata:
    """
    Data structure to store metadata for a track.
    """

    name: str
    artist: str
    album: str
    released: str
    duration: str
    image: str
    label: str
    id: str


@dataclass
class AlbumMetadata:
    """
    Data structure to store metadata for an album, including a track list.
    """

    name: str
    artist: str
    released: str
    image: str
    label: str
    id: str
    tracks: List[str]


class Spotify:
    """
    A Spotify-compatible facade that searches public metadata catalogs.

    The original BeatPrints API expected Spotify credentials. They are still
    accepted for backwards compatibility, but are no longer used.
    """

    def __init__(self, CLIENT_ID: str | None = None, CLIENT_SECRET: str | None = None):
        self.CLIENT_ID = CLIENT_ID
        self.CLIENT_SECRET = CLIENT_SECRET
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "BeatPrints-OpenMetadata/1.0 "
                    "(https://github.com/TrueMyst/BeatPrints derivative)"
                )
            }
        )

    def _format_released(self, release_date: str | None) -> str:
        if not release_date:
            return "Unknown"

        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.datetime.strptime(release_date, fmt).strftime(
                    "%B %d, %Y"
                )
            except ValueError:
                continue

        return release_date

    def _format_duration(self, duration_ms: int | float | None = None) -> str:
        if not duration_ms:
            return "00:00"

        duration_ms = int(duration_ms)
        minutes = duration_ms // 60000
        seconds = (duration_ms // 1000) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _high_res_itunes_art(self, url: str | None) -> str:
        if not url:
            return ""

        return (
            url.replace("100x100bb.jpg", "1200x1200bb.jpg")
            .replace("100x100bb.png", "1200x1200bb.png")
            .replace("60x60bb.jpg", "1200x1200bb.jpg")
            .replace("60x60bb.png", "1200x1200bb.png")
        )

    def _request_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def _track_from_itunes(self, item: dict[str, Any]) -> TrackMetadata:
        return TrackMetadata(
            name=item.get("trackName", "Unknown Track"),
            artist=item.get("artistName", "Unknown Artist"),
            album=item.get("collectionName", "Unknown Album"),
            released=self._format_released(item.get("releaseDate")),
            duration=self._format_duration(item.get("trackTimeMillis")),
            image=self._high_res_itunes_art(item.get("artworkUrl100")),
            label="Apple Music Catalog",
            id=item.get("trackViewUrl") or item.get("collectionViewUrl") or "",
        )

    def _track_from_deezer(self, item: dict[str, Any]) -> TrackMetadata:
        artist = item.get("artist") or {}
        album = item.get("album") or {}
        return TrackMetadata(
            name=item.get("title", "Unknown Track"),
            artist=artist.get("name", "Unknown Artist"),
            album=album.get("title", "Unknown Album"),
            released="Unknown",
            duration=self._format_duration((item.get("duration") or 0) * 1000),
            image=album.get("cover_xl") or album.get("cover_big") or "",
            label="Deezer Catalog",
            id=item.get("link", ""),
        )

    def _search_itunes_tracks(self, query: str, limit: int) -> List[TrackMetadata]:
        data = self._request_json(
            ITUNES_SEARCH_URL,
            {"term": query, "entity": "song", "media": "music", "limit": limit},
        )
        return [
            self._track_from_itunes(item)
            for item in data.get("results", [])
            if item.get("wrapperType") == "track"
        ]

    def _search_deezer_tracks(self, query: str, limit: int) -> List[TrackMetadata]:
        data = self._request_json(
            DEEZER_TRACK_SEARCH_URL, {"q": query, "limit": limit}
        )
        return [self._track_from_deezer(item) for item in data.get("data", [])]

    def get_track(self, query: str, limit: int = 6) -> List[TrackMetadata]:
        """
        Searches for tracks using public metadata APIs.
        """
        if limit < 1:
            raise InvalidSearchLimit

        try:
            tracks = self._search_itunes_tracks(query, limit)
        except requests.RequestException:
            tracks = []

        if not tracks:
            try:
                tracks = self._search_deezer_tracks(query, limit)
            except requests.RequestException:
                tracks = []

        if not tracks:
            raise NoMatchingTrackFound

        return tracks[:limit]

    def _album_from_itunes(self, item: dict[str, Any], shuffle: bool) -> AlbumMetadata:
        collection_id = item.get("collectionId")
        tracks: List[str] = []

        if collection_id:
            data = self._request_json(
                ITUNES_LOOKUP_URL, {"id": collection_id, "entity": "song"}
            )
            tracks = [
                result.get("trackName", "")
                for result in data.get("results", [])
                if result.get("wrapperType") == "track" and result.get("trackName")
            ]

        if shuffle:
            random.shuffle(tracks)

        return AlbumMetadata(
            name=item.get("collectionName", "Unknown Album"),
            artist=item.get("artistName", "Unknown Artist"),
            released=self._format_released(item.get("releaseDate")),
            image=self._high_res_itunes_art(item.get("artworkUrl100")),
            label="Apple Music Catalog",
            id=item.get("collectionViewUrl", ""),
            tracks=tracks,
        )

    def get_album(
        self, query: str, limit: int = 6, shuffle: bool = False
    ) -> List[AlbumMetadata]:
        """
        Searches for albums using Apple iTunes Search.
        """
        if limit < 1:
            raise InvalidSearchLimit

        try:
            data = self._request_json(
                ITUNES_SEARCH_URL,
                {"term": query, "entity": "album", "media": "music", "limit": limit},
            )
        except requests.RequestException as exc:
            raise NoMatchingAlbumFound from exc

        albums = [
            self._album_from_itunes(item, shuffle)
            for item in data.get("results", [])
            if item.get("collectionType") == "Album"
        ]

        if not albums:
            raise NoMatchingAlbumFound

        return albums[:limit]


def encode_query_url(query: str) -> str:
    return f"https://music.apple.com/us/search?term={quote_plus(query)}"

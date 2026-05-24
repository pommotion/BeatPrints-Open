"""
Module: lyrics.py

Provides functionality for retrieving song lyrics using the LRClib API.
"""

import re

from urllib.parse import quote

import requests
from lrclib import LrcLibAPI

from BeatPrints.spotify import TrackMetadata
from BeatPrints.errors import (
    NoLyricsAvailable,
    InvalidFormatError,
    InvalidSelectionError,
    LineLimitExceededError,
)
from BeatPrints.consts import Instrumental

# Initialize the components
i = Instrumental()


class Lyrics:
    """
    A class for interacting with the LRClib API to fetch and manage song lyrics.
    """

    def check_instrumental(self, metadata: TrackMetadata) -> bool:
        """
        Determines if a track is instrumental.

        Args:
            metadata (TrackMetadata): The metadata of the track.

        Returns:
            bool: True if the track is instrumental (i.e., no lyrics found), False otherwise.
        """
        api = LrcLibAPI(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
        )
        results = api.search_lyrics(
            track_name=metadata.name, artist_name=metadata.artist
        )

        return results[0].instrumental

    def get_lyrics(self, metadata: TrackMetadata) -> str:
        """
        Retrieves lyrics from LRClib.net for a specified track and artist.

        Args:
            metadata (TrackMetadata): The metadata of the track.

        Returns:
            str: The lyrics of the track in plain text if available; otherwise, a placeholder message for instrumental tracks.

        Raises:
            NoLyricsAvailable: If no lyrics are found for the specified track and artist.
        """
        lyrics, _source = self.get_lyrics_with_source(metadata)
        return lyrics

    def get_lyrics_with_source(self, metadata: TrackMetadata) -> tuple[str, str]:
        api = LrcLibAPI(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
        )
        results = api.search_lyrics(track_name=metadata.name, artist_name=metadata.artist)

        if results:
            if results[0].instrumental:
                return i.DESC, "LRCLIB"

            lyrics = api.get_lyrics_by_id(results[0].id).plain_lyrics

            if lyrics:
                return lyrics, "LRCLIB"

        fallback = self._get_lyrics_from_lyrics_ovh(metadata)
        if fallback:
            return fallback, "lyrics.ovh"

        raise NoLyricsAvailable

    def _get_lyrics_from_lyrics_ovh(self, metadata: TrackMetadata) -> str:
        artist = quote(metadata.artist, safe="")
        title = quote(metadata.name, safe="")
        try:
            response = requests.get(
                f"https://api.lyrics.ovh/v1/{artist}/{title}",
                timeout=8,
            )
        except requests.RequestException:
            return ""

        if response.status_code == 404:
            return ""

        try:
            response.raise_for_status()
        except requests.RequestException:
            return ""

        try:
            lyrics = response.json().get("lyrics", "")
        except ValueError:
            return ""
        return lyrics.replace("\r\n", "\n").strip()

    def select_lines(self, lyrics: str, selection: str) -> str:
        """
        Extracts a specific range of lines from the given song lyrics.

        Args:
            lyrics (str): The full lyrics of the song as a single string.
            selection (str): The range of lines to extract, specified in the format "start-end" (e.g., "2-5").

        Returns:
            str: A string containing exactly 4 extracted lines, separated by newline characters.

        Raises:
            InvalidFormatError: If the selection argument is not in the correct "start-end" format.
            InvalidSelectionError: If the specified range is out of bounds or otherwise invalid.
            LineLimitExceededError: If the selected range does not include exactly 4 non-empty lines.
        """

        # Split lyrics into lines
        lines = [line for line in lyrics.split("\n")]
        line_count = len(lines)

        try:
            pattern = r"^\d+-\d+$"

            # Check if selection matches the "start-end" format
            if not re.match(pattern, selection):
                raise InvalidFormatError

            selected = [int(num) for num in selection.split("-")]

            # Validate the selection range
            if (
                len(selected) != 2
                or selected[0] >= selected[1]
                or selected[0] <= 0
                or selected[1] > line_count
            ):
                raise InvalidSelectionError

            # Extract the selected lines and remove empty lines
            extracted = lines[selected[0] - 1 : selected[1]]
            selected_lines = [line for line in extracted if line != ""]

            # Ensure exactly 4 lines are selected
            if len(selected_lines) != 4:
                raise LineLimitExceededError

            quatrain = "\n".join(selected_lines).strip()
            return quatrain

        except Exception as e:
            raise e

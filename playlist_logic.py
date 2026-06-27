from typing import Dict, List, Optional, Tuple

Song = Dict[str, object]
PlaylistMap = Dict[str, List[Song]]

HYPE = "Hype"
CHILL = "Chill"
MIXED = "Mixed"
PLAYLIST_NAMES = [HYPE, CHILL, MIXED]
HYPE_KEYWORDS = ["rock", "punk", "party"]
CHILL_KEYWORDS = ["lofi", "ambient", "sleep"]

DEFAULT_PROFILE = {
    "name": "Default",
    "hype_min_energy": 7,
    "chill_max_energy": 3,
    "favorite_genre": "rock",
    "include_mixed": True,
}


def normalize_title(title: str) -> str:
    """Normalize a song title for comparisons."""
    if not isinstance(title, str):
        return ""
    return title.strip()


def normalize_artist(artist: str) -> str:
    """Normalize an artist name for comparisons."""
    if not artist:
        return ""
    return artist.strip().lower()


def normalize_genre(genre: str) -> str:
    """Normalize a genre name for comparisons."""
    return genre.lower().strip()


def to_int(value: object, default: int = 0) -> int:
    """Convert a value to an integer, falling back to a default."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_tags(tags: object) -> List[str]:
    """Normalize song tags into a clean list of strings."""
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        return []
    return [str(tag).strip().lower() for tag in tags if str(tag).strip()]


def normalize_song(raw: Song) -> Song:
    """Return a normalized song dict with expected keys."""
    title = normalize_title(str(raw.get("title", "")))
    artist = normalize_artist(str(raw.get("artist", "")))
    genre = normalize_genre(str(raw.get("genre", "")))
    energy = to_int(raw.get("energy", 0))
    tags = normalize_tags(raw.get("tags", []))

    return {
        "title": title,
        "artist": artist,
        "genre": genre,
        "energy": energy,
        "tags": tags,
    }


def song_search_text(song: Song) -> str:
    """Return searchable text for mood keyword checks."""
    title = str(song.get("title", "")).lower()
    genre = str(song.get("genre", "")).lower()
    tags = normalize_tags(song.get("tags", []))
    return " ".join([title, genre, *tags])


def contains_any_keyword(text: str, keywords: List[str]) -> bool:
    """Return True when any keyword appears in the text."""
    return any(keyword in text for keyword in keywords)


def classify_song(song: Song, profile: Dict[str, object]) -> str:
    """Return a mood label given a song and user profile."""
    energy = to_int(song.get("energy", 0))
    hype_min_energy = to_int(profile.get("hype_min_energy", 7), default=7)
    chill_max_energy = to_int(profile.get("chill_max_energy", 3), default=3)

    searchable_text = song_search_text(song)
    sounds_chill = contains_any_keyword(searchable_text, CHILL_KEYWORDS)
    sounds_hype = contains_any_keyword(searchable_text, HYPE_KEYWORDS)

    if energy <= chill_max_energy or sounds_chill:
        return CHILL
    if energy >= hype_min_energy or sounds_hype:
        return HYPE
    return MIXED


def build_playlists(songs: List[Song], profile: Dict[str, object]) -> PlaylistMap:
    """Group songs into playlists based on mood and profile."""
    playlists: PlaylistMap = {name: [] for name in PLAYLIST_NAMES}

    for song in songs:
        normalized = normalize_song(song)
        mood = classify_song(normalized, profile)
        normalized["mood"] = mood
        playlists[mood].append(normalized)

    return playlists


def merge_playlists(a: PlaylistMap, b: PlaylistMap) -> PlaylistMap:
    """Merge two playlist maps into a new map."""
    merged: PlaylistMap = {}
    playlist_names = set(list(a.keys()) + list(b.keys()))

    for key in playlist_names:
        merged[key] = list(a.get(key, []))
        merged[key].extend(b.get(key, []))
    return merged


def all_playlist_songs(playlists: PlaylistMap) -> List[Song]:
    """Return every song from every playlist."""
    songs: List[Song] = []
    for playlist_songs in playlists.values():
        songs.extend(playlist_songs)
    return songs


def compute_playlist_stats(playlists: PlaylistMap) -> Dict[str, object]:
    """Compute statistics across all playlists."""
    all_songs = all_playlist_songs(playlists)
    hype = playlists.get(HYPE, [])
    chill = playlists.get(CHILL, [])
    mixed = playlists.get(MIXED, [])

    total = len(all_songs)
    hype_ratio = len(hype) / total if total > 0 else 0.0

    avg_energy = 0.0
    if all_songs:
        total_energy = sum(to_int(song.get("energy", 0)) for song in all_songs)
        avg_energy = total_energy / total

    top_artist, top_count = most_common_artist(all_songs)

    return {
        "total_songs": len(all_songs),
        "hype_count": len(hype),
        "chill_count": len(chill),
        "mixed_count": len(mixed),
        "hype_ratio": hype_ratio,
        "avg_energy": avg_energy,
        "top_artist": top_artist,
        "top_artist_count": top_count,
    }


def most_common_artist(songs: List[Song]) -> Tuple[str, int]:
    """Return the most common artist and count."""
    counts: Dict[str, int] = {}
    for song in songs:
        artist = str(song.get("artist", ""))
        if not artist:
            continue
        counts[artist] = counts.get(artist, 0) + 1

    if not counts:
        return "", 0

    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return items[0]


def search_songs(
    songs: List[Song],
    query: str,
    field: str = "artist",
) -> List[Song]:
    """Return songs matching the query on a given field."""
    if not query:
        return songs

    q = query.lower().strip()
    filtered: List[Song] = []

    for song in songs:
        value = str(song.get(field, "")).lower()
        if value and q in value:
            filtered.append(song)

    return filtered


def songs_for_lucky_mode(playlists: PlaylistMap, mode: str) -> List[Song]:
    """Return the pool of songs allowed for a lucky pick mode."""
    if mode == "hype":
        return playlists.get(HYPE, [])
    if mode == "chill":
        return playlists.get(CHILL, [])
    return all_playlist_songs(playlists)


def lucky_pick(
    playlists: PlaylistMap,
    mode: str = "any",
) -> Optional[Song]:
    """Pick a song from the playlists according to mode."""
    return random_choice_or_none(songs_for_lucky_mode(playlists, mode))


def random_choice_or_none(songs: List[Song]) -> Optional[Song]:
    """Return a random song or None."""
    import random

    if not songs:
        return None

    return random.choice(songs)


def history_summary(history: List[Song]) -> Dict[str, int]:
    """Return a summary of moods seen in the history."""
    counts = {name: 0 for name in PLAYLIST_NAMES}
    for song in history:
        mood = song.get("mood", MIXED)
        if mood not in counts:
            counts[MIXED] += 1
        else:
            counts[mood] += 1
    return counts

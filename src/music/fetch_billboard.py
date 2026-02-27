import os
import sys

import billboard
from colorama import Fore, Style

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utilities import (
    read_file_as_list
)


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'music')

RED = Fore.RED
YELLOW = Fore.YELLOW
GREEN = Fore.GREEN
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

def fetch_billboard_top_100_tracks(bool_print=False,
                                   d=f"{MAGENTA}{BRIGHT} | {RESET}"
                                   ) -> tuple[list[billboard.BillboardChart], dict[str, int]]:
    chart = billboard.BillboardChart().chart
    artist_counts = {}
    if bool_print: print(f"{MAGENTA}{BRIGHT}=== Billboard Top 100 ==={RESET}")
    for idx,entry in enumerate(chart):
        if bool_print: print(f"{YELLOW}{idx+1:03}{RESET}{d}{entry.title} {BLUE}by{RESET} {entry.artist}", sep="\n")
        if entry.artist in artist_counts:
            artist_counts[entry.artist] += 1
        else:
            artist_counts[entry.artist] = 1
    artist_counts = dict(sorted(artist_counts.items(), key=lambda item: item[1], reverse=True))
    if bool_print: print(f"\n{MAGENTA}{BRIGHT}=== Artist Appearance Counts ==={RESET}")
    for artist, count in artist_counts.items():
        if bool_print: print(f"{artist}: {count}")
    with open(os.path.join(OUTPUT_DIR, 'billboard_top_100_tracks.txt'), 'w', encoding='utf-8') as f:
        for entry in chart:
            f.write(f"{entry.title} by {entry.artist}\n")
    return chart, artist_counts

def fetch_billboard_albums_top_200_albums(bool_print=False,
                                          d=f"{MAGENTA}{BRIGHT} | {RESET}"
                                          ) -> tuple[list[billboard.AlbumChart], dict[str, int]]:
    chart = billboard.AlbumChart().chart
    artist_counts = {}
    if bool_print: print(f"{MAGENTA}{BRIGHT}=== Billboard Top Albums ==={RESET}")
    for idx,entry in enumerate(chart):
        if bool_print: print(f"{YELLOW}{idx+1:03}{RESET}{d}{entry.title} {BLUE}by{RESET} {entry.artist}", sep="\n")
        if entry.artist in artist_counts:
            artist_counts[entry.artist] += 1
        else:
            artist_counts[entry.artist] = 1
    artist_counts = dict(sorted(artist_counts.items(), key=lambda item: item[1], reverse=True))
    if bool_print: print(f"\n{MAGENTA}{BRIGHT}=== Artist Appearance Counts ==={RESET}")
    for artist, count in artist_counts.items():
        if bool_print: print(f"{artist}: {count}")
    with open(os.path.join(OUTPUT_DIR, 'billboard_top_200_albums.txt'), 'w', encoding='utf-8') as f:
        for entry in chart:
            f.write(f"{entry.title} by {entry.artist}\n")
    return chart, artist_counts

def fetch_billboard_top_100_artists_chart(bool_print=False,
                                          d=f"{MAGENTA}{BRIGHT} | {RESET}"
                                          ) -> list[billboard.ArtistChart]:
    chart = billboard.ArtistChart().chart
    if bool_print: print(f"{MAGENTA}{BRIGHT}=== Billboard Artist Chart ==={RESET}")
    chart = sorted(chart, key=lambda entry: int(entry.weeks_on_chart), reverse=True)
    for idx,entry in enumerate(chart):
        weeks = (entry.weeks_on_chart)
        years = int(weeks) // 52
        if years > 0:
            weeks_remaining = int(weeks) % 52
            if weeks_remaining > 0:
                duration_str = f"{years} year{'s' if years > 1 else ''} and {weeks_remaining} week{'s' if weeks_remaining > 1 else ''}"
            else:
                duration_str = f"{years} year{'s' if years > 1 else ''}"
        else:
            duration_str = f"{weeks} week{'s' if int(weeks) > 1 else ''}"
        if bool_print: print(f"{YELLOW}{idx+1:03}{RESET}{d}{entry.artist}{d}{GREEN}{duration_str}{RESET} on the Top 100 Artist chart", sep="\n")
    with open(os.path.join(OUTPUT_DIR, 'billboard_top_100_artists.txt'), 'w', encoding='utf-8') as f:
        for entry in chart:
            f.write(f"{entry.artist}\n")
    return chart

def compare_artists(chart_artists: list[billboard.ArtistChart],
                    curr_artists: list[str],
                    d=f"{MAGENTA}{BRIGHT} | {RESET}",
                    bool_print=True
                    ) -> None:
    chart_artist_names = [entry.artist for entry in chart_artists]
    new_artists = [artist for artist in chart_artist_names if artist not in curr_artists]
    if new_artists:
        if bool_print: print(f"\n{MAGENTA}{BRIGHT}=== New Artists on Billboard Top 100 Artist Chart ==={RESET}")
        for artist in new_artists:
            if bool_print: print(f"{GREEN}+ {artist}{RESET}")
    else:
        if bool_print: print(f"\n{MAGENTA}{BRIGHT}=== No New Artists on Billboard Top 100 Artist Chart ==={RESET}")
    with open(os.path.join(OUTPUT_DIR, 'missing_billboard_top_100_artists.txt'), 'w', encoding='utf-8') as f:
        for artist in new_artists:
            f.write(f"{artist}\n")

if __name__ == "__main__":
    chart_tracks, artist_track_counts = fetch_billboard_top_100_tracks()
    chart_albums, artist_album_counts = fetch_billboard_albums_top_200_albums()
    chart_artists = fetch_billboard_top_100_artists_chart(bool_print=False)
    curr_artists = read_file_as_list(os.path.join(OUTPUT_DIR, 'album_artists.txt'))
    compare_artists(chart_artists, curr_artists)



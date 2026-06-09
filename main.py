import datetime as dt
import json
import os
import sys
import music_charts_archive
from spotify import Spotify

CATALOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "playlists_catalog.json")


def save_playlist(filepath: str, key, value):
    """ Add playlist name with their id and saves it as a json file """

    if os.path.exists(filepath):
        with open(filepath, mode="r") as f:
            data = json.load(fp=f)
    else:
        data = {}

    # Add new key to existing key
    data[key] = value

    # Save the whole thing back
    with open(filepath, mode="w") as f:
        json.dump(obj=data, fp=f, indent=2)
    print("Playlist added to the catalog!")


def read_catalog():
    """ Read catalog and returns json data """
    with open(CATALOG_FILE_PATH, mode="r") as f:
        data = json.load(fp=f)

    return data


def date_format(date: str):
    try:
        dt.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        print("Please use date format DDDD-MM-DD. Try again or 'X' to exit.")
        return False
    else:
        # Convert to int for comparison
        year = int(date.split("-")[0])

        if year < 1976:
            print("Please try after October 1976")
            return False
        elif year > dt.date.today().year:
            print(f"No future information yet! Please try before {dt.date.today()}. Try again or 'X' to exit.")
            return False
        else:
            return True


def main():
    # ********** STEP 1 **********
    # Initialize Spotify
    spotify = Spotify()

    done = False
    user_answer = ""
    while not done:
        # Get user date
        user_answer = input("Which year do you want to travel to? Type the date in this format YYYY-MM-DD: ")

        if date_format(user_answer):
            done = True
        elif user_answer.lower() == "x":
            print("Goodbye! ;)")
            sys.exit(0)

    # ********** STEP 2 **********
    # Get the top 50 songs from the website using the date range
    top_songs = music_charts_archive.time_machine(date=user_answer)

    # Display songs
    count = 0
    for song in top_songs:
        count += 1
        print(f"{count}. ", song)

    # ********** STEP 3 **********
    # Call spotify to search the songs URI
    spotify_songs_uri = []
    count = 0
    for song_info in top_songs:
        song_data = spotify.search_song(song=song_info[0], artist=song_info[1])

        if song_data is not None:
            get_song_uri = song_data.get("tracks").get("items")[0].get("uri")
            spotify_songs_uri.append(get_song_uri)
            count += 1
            print(f"Get song URI from spotify: {count}/{len(top_songs)}")

    print(f"Total songs URI: {len(spotify_songs_uri)}")

    # ********** STEP 4 **********
    # Create playlist
    new_playlist_name = f"Time machine week of: {user_answer}"
    playlist_metadata = spotify.create_playlist(name=new_playlist_name)

    # Get metadata
    playlist_name = playlist_metadata.get("name")
    playlist_id = playlist_metadata.get("id")

    # Add new playlist to the local catalog
    save_playlist(filepath=CATALOG_FILE_PATH, key=playlist_name, value=playlist_id)

    # Read catalog and get the playlist
    playlist_id = read_catalog().get(new_playlist_name)

    # Using the songs URI add them to the playlist
    spotify.add_song_to_playlist(playlist_id=playlist_id, spotify_uri=spotify_songs_uri)


main()

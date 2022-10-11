import random
import requests

from helpers.anilist import get_random_anime
from helpers.myanimelist import get_random_mal_anime

async def get_random_song(player):
    res = requests.post("https://anisongdb.com/api/get_50_random_songs").json()
    # If download is False, source will be a dict which will be used later to regather the stream.
    # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
    audio=None
    while audio == None:
        num1 = random.randint(0,49)
        audio = res[num1]["audio"]
    
    return await player.add_song_to_queue(res[num1])

async def get_semirandom_song(player):

    body={
            "and_logic":True,
            "ignore_duplicate":True,
            "opening_filter":player.playlist_settings["openings"],
            "ending_filter":player.playlist_settings["endings"],
            "insert_filter":player.playlist_settings["inserts"]
        }

    if player.playlist_settings["mode"] == "anime":
        body["anime_search_filter"]={"search": player.playlist_settings["param"], "partial_match": not player.playlist_settings["exact"]}
        res = requests.post("https://anisongdb.com/api/search_request",json=body).json()

    elif player.playlist_settings["mode"] == "artista":
        body["artist_search_filter"]={"search": player.playlist_settings["param"], "partial_match": not player.playlist_settings["exact"]}
        res = requests.post("https://anisongdb.com/api/search_request",json=body).json()
    else:
        return

    audio=None
    while audio == None:
        num1 = random.randint(0,len(res)-1)
        audio = res[num1]["audio"]

    return await player.add_song_to_queue(res[num1])
        

async def get_anilist_song(player):
    anilist_name = random.choice(player.playlist_settings["anilist_name"])

    songs_found=0

    while songs_found ==0:
        found_anime = await get_random_anime(anilist_name)

        body={
                "and_logic":True,
                "ignore_duplicate":True,
                "opening_filter":True,
                "ending_filter":True,
                "insert_filter":True
            }
        body["anime_search_filter"]={"search": found_anime.replace(":",""), "partial_match": True}
        res = requests.post("https://anisongdb.com/api/search_request",json=body).json()

        songs_found=len(res)

    audio=None
    while audio == None:
        num1 = random.randint(0,len(res)-1)
        audio = res[num1]["audio"]
    res[num1]["list"]=anilist_name
    return await player.add_song_to_queue(res[num1])

async def get_mal_song(player):
    mal_name = random.choice(player.playlist_settings["mal_name"])

    songs_found=0

    while songs_found ==0:
        found_anime = await get_random_mal_anime(mal_name)

        body={
                "and_logic":True,
                "ignore_duplicate":True,
                "opening_filter":player.playlist_settings["openings"],
                "ending_filter":player.playlist_settings["endings"],
                "insert_filter":player.playlist_settings["inserts"]
            }
        body["anime_search_filter"]={"search": found_anime, "partial_match": True}
        res = requests.post("https://anisongdb.com/api/search_request",json=body).json()

        songs_found=len(res)

    audio=None
    while audio == None:
        num1 = random.randint(0,len(res)-1)
        audio = res[num1]["audio"]
    res[num1]["list"]=mal_name
    return await player.add_song_to_queue(res[num1])
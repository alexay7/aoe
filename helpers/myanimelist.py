import os
import requests
from numpy.random import random_integers

async def get_random_mal_anime(username):
    query_url = f"https://api.myanimelist.net/v2/users/{username}/animelist?limit=1000&status=completed"

    headers = {
        "X-MAL-CLIENT-ID":os.getenv("MAL_ID")
    }

    response = requests.get(query_url,headers=headers).json()

    anime_name = None

    while anime_name==None:
        random_num = random_integers(0,999)
        try:
            anime_url = f"https://api.myanimelist.net/v2/anime/{response['data'][random_num]['node']['id']}?fields=alternative_titles"
            anime_info = requests.get(anime_url,headers=headers).json()
            anime_name = anime_info["alternative_titles"]["en"] or anime_info["title"]
        except:
            ...
    return anime_name
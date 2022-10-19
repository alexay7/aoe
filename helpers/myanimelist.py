import os
from time import sleep
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

async def get_all_animes(username):
    query_url = f"https://api.myanimelist.net/v2/users/{username}/animelist?limit=1000&status=completed"
    headers = {
        "X-MAL-CLIENT-ID":os.getenv("MAL_ID")
    }
    animes=[]
    response = requests.get(query_url,headers=headers).json()["data"]
    for elem in response:
        anime_url = f"https://api.myanimelist.net/v2/anime/{elem['node']['id']}?fields=alternative_titles"
        anime_info = requests.get(anime_url,headers=headers).json()
        anime_name = anime_info["alternative_titles"]["en"] or anime_info["title"]
        animes.append({
            "english":anime_name,
            "original":anime_info["title"]
        })
        print({
            "english":anime_name,
            "original":anime_info["title"]
        })
    return animes
import math
from numpy.random import random_integers
import requests


async def get_anilist_info(username):
    query = '''
    query ($username: String){
  User(name:$username){
        id,
        statistics{
            anime{
                statuses{
                    count
                }
            }
        }
        }
    }
    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'username': username
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    res = requests.post(
        url, json={'query': query, 'variables': variables}).json()

    if "errors" in res:
        print(res)
        return -1
    else:
        return {"user_id":res["data"]["User"]["id"],
        "total":res["data"]["User"]["statistics"]["anime"]["statuses"][0]["count"]}

async def get_random_anime(username):
    result = await get_anilist_info(username)

    total_pages = math.ceil(int(result["total"])/50)
    
    random_page = random_integers(1,total_pages)
    
    query = '''
    query($page:Int, $userId:Int){
  Page(page:$page,perPage:50){
    pageInfo{
      hasNextPage
      lastPage
      currentPage
    }
    mediaList(userId: $userId,type:ANIME,status_in:[COMPLETED,CURRENT]) {
      id
      media{
        title {
          romaji
          english
          native
          userPreferred
        },
        format,
        episodes,
        duration
      },
      completedAt {
        year
        month
        day
      },
      startedAt {
        year
        month
        day
      }
      status
  }
  }
}

    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'userId': result["user_id"],
        'page': str(random_page)
    }

    url = 'https://graphql.anilist.co'

    anime = None

    while anime==None:
        random_num = random_integers(0,49)
        # Make the HTTP Api request
        data = requests.post(
            url, json={'query': query, 'variables': variables}).json()
        try:
            anime = data["data"]["Page"]["mediaList"][random_num]["media"]["title"]["romaji"]
        except:
            ...
            
    return anime

# 115 PAGES

#     {Page(page:1,perPage:50){
#   pageInfo{
#     total perPage currentPage lastPage hasNextPage
#   }
#   media(
#     genre_in:["Comedy"],sort:END_DATE_DESC,status:FINISHED,startDate_greater:19000101){
#         id title{romaji}{edges{isMain node{id name}}}}}}
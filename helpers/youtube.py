import asyncio
import discord
from youtube_dl import YoutubeDL

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester): 
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        self.artist = data.get("artist")
        self.anime = data.get("anime")
        self.season = data.get("season")
        self.type = data.get("type")
        self.filename=data.get("filename")
        self.ann_id=data.get("annId")
        self.video_url=data.get("videoUrl")

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.

        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def from_url(cls, ctx, songData, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(songData["audio"], download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)

        songInfo = {
            "title":songData["songName"],
            "artist":songData["songArtist"],
            "anime":songData["animeJPName"],
            "season":songData["animeVintage"],
            "type":songData["songType"],
            "filename":filename,
            "annId":songData["annId"],
            "videoUrl":songData["HQ"]
        }
        return cls(discord.FFmpegPCMAudio(filename), data=songInfo, requester=ctx.author)
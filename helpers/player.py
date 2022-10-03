import asyncio
import os
import random
import shutil
import traceback
import discord
import requests
from async_timeout import timeout
import urllib3
from helpers.youtube import YTDLSource
import xmltodict

def empty_downloads():
    folder = 'downloads'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            ...

class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.

    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.

    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume','playlist_settings','_ctx')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._ctx = ctx
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue(maxsize=5)
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .25
        self.current = None
        self.playlist_settings = {
            "randomize":False,
            "userList":0,
            "openings":True,
            "endings":True,
            "inserts":False
        }

        ctx.bot.loop.create_task(self.player_loop())

    async def get_random_song(self, ctx):
        res = requests.post("https://anisongdb.com/api/get_50_random_songs").json()
        source1 = await YTDLSource.from_url(ctx, res[random.randint(0,49)], loop=self.bot.loop)
        print(f"Added {source1.title}")
        await self.queue.put(source1)

        source2 = await YTDLSource.from_url(ctx, res[random.randint(0,49)], loop=self.bot.loop)
        print(f"Added {source2.title}")
        await self.queue.put(source2)

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            empty_downloads()
            self.next.clear()

            if(self.playlist_settings["randomize"]):
                asyncio.ensure_future(self.get_random_song(self._ctx))

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            url = f"https://cdn.animenewsnetwork.com/encyclopedia/api.xml?anime={source.ann_id}"

            http = urllib3.PoolManager()

            response = http.request('GET', url)
            try:
                data = xmltodict.parse(response.data)
            except:
                print("Failed to parse xml from response (%s)" % traceback.format_exc())

            image = data["ann"]["anime"]["info"][0]["@src"]
            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            embed = discord.Embed(title="Reproduciendo ahora: ",color=0x0061ff)
            embed.set_thumbnail(url=image)
            embed.add_field(name="Nombre de la Canción",value=source.title)
            embed.add_field(name="Artista",value=source.artist)
            embed.add_field(name="Tipo",value=source.type,inline=False)
            embed.add_field(name="Anime",value=source.anime,inline=False)
            embed.add_field(name="Season",value=source.season,inline=True)
            embed.add_field(name="Vídeo",
                                   value=f"[{source.title}]({source.video_url})")
            self.np = await self._channel.send(embed=embed)
            await self.next.wait()
            await asyncio.sleep(2)

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))

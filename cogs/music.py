"""
Please understand Music bots are complex, and that even this basic example can be daunting to a beginner.

For this reason it's highly advised you familiarize yourself with discord.py, python and asyncio, BEFORE
you attempt to write a music bot.

This example makes use of: Python 3.6

For a more basic voice example please read:
    https://github.com/Rapptz/discord.py/blob/rewrite/examples/basic_voice.py

This is a very basic playlist example, which allows per guild playback of unique queues.
The commands implement very basic logic for basic usage. But allow for expansion. It would be advisable to implement
your own permissions and usage logic for commands.

e.g You might like to implement a vote before skipping the song or only allow admins to stop the player.

Music bots require lots of work, and tuning. Goodluck.
If you find any bugs feel free to ping me on discord. @Eviee#0666
"""
import json
import os
import random
import shutil
import discord
from discord.ext import commands
import urllib3
from helpers.messages import send_message_with_buttons
from helpers.player import MusicPlayer
from helpers.youtube import YTDLSource

import asyncio
import itertools
import sys
import traceback
import requests
import xmltodict
import urllib

class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""

class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error conectando al canal de voz. '
                           'Asegúrate de que estás en un canal de voz válido')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(name='connect', aliases=['join'])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
        """Connect to voice.

        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.

        This command also handles moving the bot to different channels.
        """
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel('No se ha encontrado el canal, únete a uno o indícame cual es.')

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moviéndome al canal: <{channel}> no se pudo conectar.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Conectándome al canal: <{channel}> no se pudo conectar.')

        await ctx.send(f'Connected to: **{channel}**', delete_after=20)

    @commands.command(name='play', aliases=['sing'])
    async def play_(self, ctx, song, anime):
        """Request a song and add it to the queue.

        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.

        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
        # await ctx.trigger_typing()

        vc = ctx.voice_client
        player = self.get_player(ctx)

        if not vc:
            await ctx.invoke(self.connect_)
        res = requests.post("https://anisongdb.com/api/search_request",
                            json={"song_name_search_filter": {"search": song, "partial_match": True}, "anime_search_filter": {"search": anime, "partial_match": True}}).json()

        if(player.playlist_settings["randomize"]):
            await ctx.send("Modo aleatorio desactivado")
        player.playlist_settings["randomize"]=False
        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        message:discord.Message = await ctx.send("Descargando canción...")
        source = await YTDLSource.from_url(ctx, res[0], loop=self.bot.loop)
        await message.delete()

        await player.queue.put(source)

    @commands.command(name="buscar")
    async def selector_(self,ctx,song):
        res = requests.post("https://anisongdb.com/api/search_request",
                            json={"song_name_search_filter": {"search": song, "partial_match": True}}).json()

        vc = ctx.voice_client
        player = self.get_player(ctx)

        if not vc:
            await ctx.invoke(self.connect_)

        message=""
        index=1
        for elem in res:
            if index<12:
                message+=f"{index}) {elem['songName']} - {elem['songArtist']}\n"
                index+=1

        player = self.get_player(ctx)
    
        await ctx.send(message)
        response = await self.bot.wait_for("message",check=lambda message:message.author == ctx.author)
        if response.content.isnumeric():
            message:discord.Message = await ctx.send("Descargando canción...")
            source = await YTDLSource.from_url(ctx, res[int(response.content)-1], loop=self.bot.loop)
            await message.delete()

        await player.queue.put(source)

    @commands.command(name='random')
    async def random_(self, ctx):
        """Request a song and add it to the queue.

        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.

        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
        # await ctx.trigger_typing()

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect_)

        player = self.get_player(ctx)

        if(not player.playlist_settings["randomize"]):
            await ctx.send("Modo aleatorio activado")

        res = requests.post("https://anisongdb.com/api/get_50_random_songs").json()
        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.from_url(ctx, res[random.randint(0,49)], loop=self.bot.loop)
        player.playlist_settings["randomize"]=True

        await player.queue.put(source)

    @commands.command(name='pause')
    async def pause_(self, ctx):
        """Pause the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.send(f'**`{ctx.author}`**: Ha pausado la música.')

    @commands.command(name='resume')
    async def resume_(self, ctx):
        """Resume the currently paused song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.send(f'**`{ctx.author}`**: Ha reanudado la música.')

    @commands.command(name='skip')
    async def skip_(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(f'**`{ctx.author}`**: Ha saltado la canción.')

    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def queue_info(self, ctx):
        """Retrieve a basic queue of upcoming songs."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('¡No estoy en ningún canal de voz!', delete_after=20)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('No hay canciones en la cola.')

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(title=f'Próxima canción - Next {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed)

    @commands.command(name='now_playing', aliases=['np', 'current', 'currentsong', 'playing'])
    async def now_playing_(self, ctx):
        """Display information about the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('¡No estoy en ningún canal de voz!', delete_after=20)

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send('¡No se está reproduciendo ninguna canción!')

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass
        
        url = "https://cdn.animenewsnetwork.com/encyclopedia/api.xml?anime=21469"

        http = urllib3.PoolManager()

        response = http.request('GET', url)
        try:
            data = xmltodict.parse(response.data)
        except:
            print("Failed to parse xml from response (%s)" % traceback.format_exc())

        image = data["ann"]["anime"]["info"][0]["@src"]

        player.np = await ctx.send(f'**Reproduciendo:** `{vc.source.title}` '
                                   f'pedida por `{vc.source.requester}`')

    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, ctx, *, vol: float=-1):
        """Change the player volume.

        Parameters
        ------------
        volume: float or int [Required]
            The volume to set the player to in percentage. This must be between 1 and 100.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('¡No estoy en ningún canal de voz!', delete_after=20)

        if vol==-1:
            return await ctx.send(f'El volumen actual es {player.volume}%')

        if not 0 < vol < 101:
            return await ctx.send('Introduce un valor entre 1 y 100.')

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await ctx.send(f'**`{ctx.author}`**: Fijó el volumen en **{vol}%**')

    @commands.command(name='stop')
    async def stop_(self, ctx):
        """Stop the currently playing song and destroy the player.

        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)

        await self.cleanup(ctx.guild)


async def setup(bot):
    await bot.add_cog(Music(bot))
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
from collections import Counter
import datetime
import json
from operator import attrgetter
import os
import random
import shutil
import discord
from discord.ext import commands
from matplotlib import artist
import urllib3
from helpers.anilist import get_random_anime
from helpers.messages import send_message_with_buttons
from helpers.myanimelist import get_all_animes, get_random_mal_anime
from helpers.player import MusicPlayer
from helpers.songs import get_all_songs, get_anilist_song, get_mal_song, get_random_song, get_semirandom_song
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

    def __init__(self, bot:discord.Bot):
        self.bot = bot
        self.players = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de musica cargado con éxito")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction,user):
        try:
            ctx = await self.bot.get_application_context(user)
            if not user.bot:
                if reaction.emoji=="⏭️":
                    await ctx.invoke(self.skip_)
                elif reaction.emoji=="⏸️":
                    await ctx.invoke(self.pause_)
                elif reaction.emoji=="▶️":
                    await ctx.invoke(self.resume_)
                elif reaction.emoji=="⏹️":
                    await ctx.invoke(self.stop_)
                return await reaction.remove()
        except:
            ...

            


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

    @commands.command(name="radio")
    async def listenradio_(self,ctx,url="https://listen.moe/fallback"):
        """Connect to listen.moe radio"""
        vc:discord.VoiceClient = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect_)
            vc = ctx.voice_client
        vc.play(discord.FFmpegPCMAudio(url))
        vc.source = discord.PCMVolumeTransformer(vc.source,volume=.1)
        

        embed = discord.Embed(title="Reproduciendo ahora: ",color=0x0061ff)
        embed.add_field(name="Modo",value="Lista de reproducción externa")
        self.np:discord.Message = await ctx.send(embed=embed)
        await self.np.add_reaction(emoji="▶️")
        await self.np.add_reaction(emoji="⏸️")

    @commands.command("listaradios")
    async def listaradios_(self,ctx):
        await ctx.send("https://github.com/LaQuay/TDTChannels/blob/master/RADIO.md",delete_after=30.0)

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

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        message:discord.Message = await ctx.send("Descargando canción...")
        source = await YTDLSource.from_url(ctx, res[0], loop=self.bot.loop)
        await message.delete()

        await player.queue.put(source)

    @commands.command()
    async def buscar(self,ctx):
        await ctx.send("Este comando solo funciona con /",delete_after=10.0)

    @commands.slash_command(name="playlist")
    async def artistplaylist_(self,ctx,
        modo: discord.Option(str, "Playlist de artista o anime", required=True, choices=["artista","anime"]),
        nombre: discord.Option(str, "Artista/Anime a buscar", required=False),
        genre: discord.Option(str, "Género a buscar", required=False),
        openings: discord.Option(bool, "Buscar openings (default: true)", default=True),
        endings: discord.Option(bool, "Buscar endings (default: true)", default=True),
        inserts: discord.Option(bool, "Buscar inserts (default: false)", default=False),
        exacto:discord.Option(bool,"Buscar nombre exacto",default=False)
    ):

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect_)

        await ctx.defer()
        player = self.get_player(ctx)
        player.playlist_settings["mode"]=modo
        player.playlist_settings["openings"]=openings
        player.playlist_settings["endings"]=endings
        player.playlist_settings["inserts"]=inserts
        player.playlist_settings["exact"]=exacto

        if nombre:
            player.playlist_settings["param"]=nombre
        if genre:
            player.playlist_settings["genre"]=genre

        if modo == "artista" and not nombre:
            return await ctx.respond("Tienes que concretar el artista!",delete_after=10)

        if modo == "anime" and not nombre:
            return await ctx.respond("Tienes que concretar el anime!",delete_after=10)

        if modo == "anilist" and not nombre and not genre:
            return await ctx.respond("Tienes que concretar el usuario de anilist o el género del anime!",delete_after=10)

        await get_semirandom_song(player)
        await ctx.respond("Playlist cargada con éxito")
        # artista -> busca en la base de datos directamente
        # anime -> busca en la base de datos directamente
        # anilist -> busca en anilist, si hay género solo busca cosas del género dicho

    @commands.slash_command(name="anilist")
    async def anilistplay_(self,ctx,
    anilistname:discord.Option(str,"Nombre de anilist",required=True)):

        await ctx.defer()

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect_)

        player = self.get_player(ctx)
        player = self.get_player(ctx)
        player.playlist_settings["mode"]="anilist"
        if anilistname in player.playlist_settings["anilist_name"]:
            return await ctx.respond("Esa lista ya está cargada!",delete_after=5.0)
        player.playlist_settings["anilist_name"].append(anilistname)
        try:
            await get_anilist_song(player)
        except:
            return await ctx.respond("Ha ocurrido un error cargando la cuenta de anilist")
        return await ctx.respond(f"Cargada con éxito la cuenta de anilist de {anilistname}",delete_after=10.0)

    @commands.slash_command(name="myanimelist")
    async def myanimelistplay_(self,ctx,
    malname:discord.Option(str,"Nombre de myanimelist",required=True),
    openings: discord.Option(bool, "Buscar openings (default: true)", default=True),
        endings: discord.Option(bool, "Buscar endings (default: true)", default=True),
        inserts: discord.Option(bool, "Buscar inserts (default: true)", default=False),
    ):
        await ctx.defer()

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect_)

        player = self.get_player(ctx)
        player.playlist_settings["mode"]="mal"
        if malname in player.playlist_settings["mal_name"]:
            return await ctx.respond("Esa lista ya está cargada!",delete_after=5.0)
        player.playlist_settings["mal_name"].append(malname)
        player.playlist_settings["openings"]=openings
        player.playlist_settings["endings"]=endings
        player.playlist_settings["inserts"]=inserts
        
        try:
            await get_mal_song(player)
        except:
            return await ctx.respond("Ha ocurrido un error cargando la cuenta de myanimelist")
        return await ctx.respond(f"Cargada con éxito la cuenta de myanimelist de {malname}",delete_after=10.0)

    @commands.slash_command(name="quitarmal")
    async def removemyanimelist_(self,ctx,
        malname:discord.Option(str,"Nombre de myanimelist a borrar",required=True),
    ):
        player = self.get_player(ctx)
        if malname in player.playlist_settings["mal_name"]:
            player.playlist_settings["mal_name"].remove(malname)

        await ctx.respond("Lista quitada con éxito")

    @commands.slash_command(name="quitaranilist")
    async def removeanilist_(self,ctx,
        anilistname:discord.Option(str,"Nombre de anilist a borrar",required=True),
    ):
        player = self.get_player(ctx)
        if anilistname in player.playlist_settings["anilist_name"]:
            player.playlist_settings["anilist_name"].remove(anilistname)

        await ctx.respond("Lista quitada con éxito")

    @commands.command(name="historial",aliases=["h","history"])
    async def gethistory_(self,ctx):
        with open("temp/history.txt","r",encoding="utf-8") as file:
            text=f"```{file.read()}```"
            file.close()
        await ctx.send(text)
        

    @commands.command(name='aleatorio',aliases=['random'])
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

        if(player.playlist_settings["mode"]!="random"):
            await ctx.send("Modo aleatorio activado")
            player.playlist_settings["mode"]="random"
        else:
            await ctx.send("Modo aleatorio desactivado")
            player.playlist_settings["mode"]=""
            return

        await get_random_song(player)

    @commands.slash_command(name="buscar")
    async def selector_(self,ctx,
        canción: discord.Option(str, "Canción a buscar", required=False),
        anime: discord.Option(str, "Anime a buscar", required=False), 
        artista: discord.Option(str, "Artista a buscar", required=False),
        exacto:discord.Option(bool,"Buscar nombre exacto",default=False)):
        """Buscar una canción para reproducir"""
        await ctx.defer()
        body={
            "and_logic":True,
            "ignore_duplicate":True
        }

        current_time = datetime.datetime.now()

        if not canción and not artista and not anime:
            await ctx.respond("Tienes que rellenar al menos uno de los 3 parámetros",delete_after=10)
            return

        if (canción or artista) and ((current_time.minute>30 and current_time.hour in [13,20,6]) or (current_time.minute<30 and current_time.hour in [14,21,7])):
            if anime:
                await ctx.send("Ahora mismo hay una ranked en progreso así que solo se tendrá en cuenta el campo de anime",delete_after=10)
            else:
                await ctx.respond("Ahora mismo hay una ranked en progreso así que solo se pueden buscar canciones por anime",delete_after=10)
                return

        if canción:
            body["song_name_search_filter"]={"search": canción, "partial_match": not exacto}

        if anime:
            body["anime_search_filter"]={"search": anime, "partial_match": not exacto}

        if artista:
            body["artist_search_filter"]={"search": artista, "partial_match": not exacto}

        res = requests.post("https://anisongdb.com/api/search_request",
                            json=body).json()
        vc = ctx.voice_client
        player = self.get_player(ctx)

        if not vc:
            await ctx.invoke(self.connect_)

        message=""
        index=1
        if len(res)==0:
            await ctx.respond("No se encontraron resultados",delete_after=10.0)
            return
        elif len(res)==1:
            message:discord.Message = await ctx.send("Descargando canción...")
            source = await YTDLSource.from_url(ctx, res[0], loop=self.bot.loop)
            await message.delete()
        else:
            for elem in res:
                if index<15 and elem["audio"]!=None:
                    message+=f"{index}) {elem['songName']} - {elem['songArtist']} ({elem['songType']}) [{elem['animeJPName']}]\n"
                    index+=1

            player = self.get_player(ctx)
        
            song_list = await ctx.send(message,delete_after=30)
            response = await self.bot.wait_for("message",check=lambda message:message.author == ctx.author and message.content.isnumeric() or message.content == "x")
            if response.content.isnumeric():
                await song_list.delete()
                message:discord.Message = await ctx.send("Descargando canción...")
                source = await YTDLSource.from_url(ctx, res[int(response.content)-1], loop=self.bot.loop)
                await message.delete()

        await player.queue.put(source)
        
        await ctx.respond(f"{source.title} añadida con éxito en la posición {player.queue.qsize()} de la cola!",delete_after=15.0)

    @commands.command(name='pausa',aliases=['pause'])
    async def pause_(self, ctx:discord.ApplicationContext):
        """Pause the currently playing song."""
        vc = ctx.voice_client
        
        if "interaction" in ctx.__dict__:
            user:discord.Member = ctx.__dict__["interaction"]
            if not user.voice or user.voice.channel.id != vc.channel.id:
                await ctx.send("Si no estás en el vc no decides las canciones",delete_after=10.0)

        if not vc or not vc.is_playing():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.send(f'**`{ctx.author}`**: Ha pausado la música.')

    @commands.command(name='reanudar',aliases=['resume'])
    async def resume_(self, ctx):
        """Resume the currently paused song."""
        vc = ctx.voice_client

        if "interaction" in ctx.__dict__:
            user:discord.Member = ctx.__dict__["interaction"]
            if not user.voice or user.voice.channel.id != vc.channel.id:
                await ctx.send("Si no estás en el vc no decides las canciones",delete_after=10.0)

        if not vc or not vc.is_connected():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.send(f'**`{ctx.author}`**: Ha reanudado la música.')

    @commands.command(name='saltar',aliases=['skip'])
    async def skip_(self, ctx:discord.ApplicationContext):
        """Skip the song."""
        vc:discord.VoiceClient = ctx.voice_client

        if "interaction" in ctx.__dict__:
            user:discord.Member = ctx.__dict__["interaction"]
            if not user.voice or user.voice.channel.id != vc.channel.id:
                await ctx.send("Si no estás en el vc no decides las canciones",delete_after=10.0)

        if not vc or not vc.is_connected():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return


        vc.stop()
        await ctx.send(f'**`{ctx.author}`**: Ha saltado la canción.')

    @commands.command(name='cola', aliases=['q','queue'])
    async def queue_info(self, ctx):
        """Retrieve a basic queue of upcoming songs."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('¡No estoy en ningún canal de voz!', delete_after=20)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('No hay canciones en la cola.',delete_after=10)

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**`{_["title"]} - {_["artist"]} [{_["anime"]}]`**' for _ in upcoming)
        embed = discord.Embed(title=f'Próxima canción - Pendientes: {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed,delete_after=15)

    @commands.command(name='info', aliases=['np', 'current', 'currentsong', 'playing'])
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
        
        url = f"https://cdn.animenewsnetwork.com/encyclopedia/api.xml?anime={player.current.ann_id}"

        http = urllib3.PoolManager()

        response = http.request('GET', url)
        try:
            data = xmltodict.parse(response.data)
        except:
            print("Failed to parse xml from response (%s)" % traceback.format_exc())

        image = data["ann"]["anime"]["info"][0]["@src"]
        source=player.current

        embed = discord.Embed(title="Reproduciendo ahora: ",color=0x0061ff)
        if "@src" in data["ann"]["anime"]["info"][0]:
            image = data["ann"]["anime"]["info"][0]["@src"]
            embed.set_thumbnail(url=image)
        embed.add_field(name="Canción",value=source.title)
        embed.add_field(name="Artista",value=source.artist)
        embed.add_field(name="Tipo",value=source.type,inline=False)
        embed.add_field(name="Anime",value=source.anime,inline=False)
        embed.add_field(name="Season",value=source.season,inline=True)
        embed.add_field(name="Vídeo",
                                value=f"[{source.title}]({source.video_url})")
        player.np = await ctx.send(embed=embed)

    @commands.command(name='volumen', aliases=['vol','volume'])
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

    @commands.command(name='parar',aliases=['stop'])
    async def stop_(self, ctx):
        """Stop the currently playing song and destroy the player.

        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = ctx.voice_client
        player = self.get_player(ctx)
        for _ in range(player.queue.qsize()):
            # Depending on your program, you may want to
            # catch QueueEmpty
            player.queue.get_nowait()
            player.queue.task_done()

        if "interaction" in ctx.__dict__:
            user:discord.Member = ctx.__dict__["interaction"]
            if not user.voice or user.voice.channel.id != vc.channel.id:
                await ctx.send("Si no estás en el vc no decides las canciones",delete_after=10.0)

        if not vc or not vc.is_connected():
            return await ctx.send('¡No se está reproduciendo ninguna canción!', delete_after=20)

        await self.cleanup(ctx.guild)

    @commands.command(name="download")
    async def downloadlist_(self,ctx,username):
        all_songs = []
        anime_list = await get_all_animes(username)
        for elem in anime_list:
            song_list = await get_all_songs(elem["english"])
            if(elem["english"]!=elem["original"]):
                song_list+= await get_all_songs(elem["original"])
            for song in song_list:
                if song not in all_songs:
                    print(song)
                    all_songs.append(song)
                else:
                    print("repeated song",song)
        with open(f"temp/{username}.json","w",encoding="utf-8") as file:
            json.dump(all_songs,file)
            await ctx.send(f"Registradas todas las canciones de: {username}")
                
    @commands.command(name="stats")
    async def getstats_(self,ctx,username):
        try:
            with open(f"temp/{username}.json","r",encoding="utf-8") as file:
                data = json.load(file)
        except:
            await ctx.send("Tu lista de anime no está registrada, para cargarla usa el comando &download [nombredemal]",delete_after=10.0)
            return
        total = len(data)
        counted = Counter((song["artist"]) for song in data)
        output = [Item(artist, k) for (artist), k in counted.items()]
        sorted_output = sorted(output,key=lambda x:x.count,reverse=True)

        artist_list = ""
        index=1
        for elem in sorted_output:
            if(index>50):
                break
            artist_list+=f"{index}º) {elem.artist}: {str(elem.count)}\n"
            index+=1
        await ctx.send(f"-- CANCIONES DE {username} TOTAL:{total}--\n```{artist_list}``` ",delete_after=60)

    @commands.command(name="compare")
    async def compare_(self,ctx,username1,username2):
        try:
            with open(f"temp/{username1}.json","r",encoding="utf-8") as file:
                data1 = json.load(file)
        except:
            await ctx.send("Tu lista de anime no está registrada, para cargarla usa el comando &download [nombredemal]",delete_after=10.0)
            return
        try:
            with open(f"temp/{username2}.json","r",encoding="utf-8") as file:
                data2 = json.load(file)
        except:
            await ctx.send("Tu lista de anime no está registrada, para cargarla usa el comando &download [nombredemal]",delete_after=10.0)
            return
        common = []
        for elem in data1:
            if(elem in data2):
                common.append(elem)
        shared = len(common)
        counted = Counter((song["artist"]) for song in common)
        output = [Item(artist, k) for (artist), k in counted.items()]
        sorted_output = sorted(output,key=lambda x:x.count,reverse=True)

        artist_list = ""
        index=1
        for elem in sorted_output:
            if(index>50):
                break
            artist_list+=f"{index}º) {elem.artist}: {str(elem.count)}\n"
            index+=1
        await ctx.send(f"-- CANCIONES EN COMÚN ENTRE {username1} Y {username2} Total:{shared}--\n```{artist_list}```",delete_after=60)

class Item:
    def __init__(self, artist, count):
        self.artist = artist
        self.count = count

    def __repr__(self):
        return '{"artist":'+self.artist+',"count":'+str(self.count)+'}'

        

def setup(bot):
    bot.add_cog(Music(bot))
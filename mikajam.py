#!/usr/bin/env python

import os
import youtube_dl
import asyncio
import discord
import itertools

from discord.ext import commands
from discord.utils import get
from discord.ext.tasks import loop

from functools import partial

from async_timeout import timeout


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}


ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=True):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        await ctx.send(f'\n> Added **{data["title"]}** to the Queue.\n', delete_after=15)

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=True)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


# Literal Player (Separate for OOP)
class MikaPlayer:

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')
    
    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = "OOf"  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())


    # Main Loop
    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(300):  # 5 minutes bruh
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing the song\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'> **Now Playing** {source.title} asked by '
                                               f'{source.requester}')
            await self.next.wait()

            # Make sure the FFmpeg picks up trash
            source.cleanup()
            self.current = None

            try:
                # Song is a nono
                await self.np.delete()
            except discord.HTTPException:
                pass


    # Clean the garbo
    def destroy(self, guild):
        return self.bot.loop.create_task(self._cog.cleanup(guild))


# Music Commands bruh
class Mikajam(commands.Cog):

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}


    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
            os.system("rm -f youtube-*")
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass


    async def __local_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True


    async def __error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in private messages')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('> Error connecting to voice, '
                           'please make sure you are in a valid channel or you provided me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


    # Get server player or create one out of thin air
    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MikaPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player


    # Use this command to yeet Mikasa across different channels
    @commands.command(name='connect', aliases=['join'])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

        await ctx.send(f'> Swung to **{channel}**', delete_after=20)


    # Request a song and add it to the queue, will attempt to join to a channel
    @commands.command(name='play', aliases=['sing'])
    async def play_(self, ctx, *, search: str):
        await ctx.trigger_typing()

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect_)

        player = self.get_player(ctx)

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=True)

        await player.queue.put(source)


    # Self explanatory
    @commands.command(name='pause')
    async def pause_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            await ctx.send('No song is playing')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")
        elif vc.is_paused():
            await ctx.send('Its already paused')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        vc.pause()
        await ctx.send(f'> **Muisc paused**')


    # Self explanatory
    @commands.command(name='resume')
    async def resume_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            await ctx.send('No song is playing')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")
        elif not vc.is_paused():
            await ctx.send("Music isn't paused")
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        vc.resume()
        await ctx.send(f'> **Music resuming**')


    # Self explanatory
    @commands.command(name='skip')
    async def skip_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            await ctx.send('No song is playing')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(f'> **Music skipped**')


    # Retrieve the queue
    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def queue_info(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            await ctx.send("I'm not even in voice")
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('> No more songs in queue')

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**{_["title"]}**' for _ in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed)

    
    # Get info of now playing music
    @commands.command(name='now_playing', aliases=['np', 'current', 'currentsong', 'playing'])
    async def now_playing_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            await ctx.send('No song is playing')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        player = self.get_player(ctx)
        if not player.current:
            await ctx.send('No song is playing')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass

        player.np = await ctx.send(f'> **Now Playing** {vc.source.title}'
                                   f'asked by {vc.source.requester}')


    # Change volume
    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, ctx, *, vol: float):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            await ctx.send('No song is playing')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        if not 0 < vol < 101:
            await ctx.send('Put a number between 1 and 100, use your common sense')
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await ctx.send(f'> **{ctx.author}** made the volume to **{vol}%**')


    # Halt and murder the player
    @commands.command(name='stop')
    async def stop_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            await ctx.send("How can I stop something if that something doesn't exist")
            mik = get(ctx.guild.emojis, name="why_mikasa")
            return await ctx.send(f"{mik}")


        await self.cleanup(ctx.guild)

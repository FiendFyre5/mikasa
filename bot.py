#!/usr/bin/env python

# Imports
import os
import asyncio
import youtube_dl
import discord

from discord.ext import commands
from dotenv import load_dotenv


# Load token from env vars
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


# Paths for files
mikasa_scarf_gif = "media/mikasa_scarf.gif"
mikasa_stare_gif = "media/mikasa_stare.gif"


"""
# no ID, do a lookup
emoji = discord.utils.get(guild.emojis, name='LUL')
if emoji:
    await message.add_reaction(emoji)
"""


# Emojis
anger_emoji = 736335946060136480
mikasa_ded_emoji = 745556147376881714
creepy_annie_emoji = 745854948947918858
knife_emoji = "\U0001f5e1"
yes_emoji = "\U00002705"
maybe_emoji = "\U0001F937"
no_emoji = "\U0000274E"
# Sweak Jar
swear_rank = {}


bot = commands.Bot(command_prefix=commands.when_mentioned_or("-"),
                   description='Relatively simple music bot example')


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
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot


    # Force join into a vc (-join general)
    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

   # Plays from yt with dl
    @commands.command()
    async def play(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error -> %s' % e) if e else None)
        await ctx.send('Now playing -> {}'.format(player.title))


    # Streams from yt (does not work, has a time limit (yt fault))
    @commands.command()
    async def stream(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error -> %s' % e) if e else None)
        await ctx.send('Now playing -> {}'.format(player.title))


    # Volume
    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("I am not in a voice channel")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Volume changed to {}%".format(volume))


    # Disconnect from voice
    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()


    # Makes sure someone is on voice
    @play.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send(ctx.author.mention + " You are not in a voice channel")
                raise commands.CommandError("User not in voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


# Hello command
@bot.command(pass_context=True) 
async def hello(ctx, *args):
    await ctx.message.channel.send('EREN!')


# Pin command
@bot.command(pass_context=True)
async def pin(ctx, *args):
    if 'remove' in ctx.message.content:
        print("hello")
        pins = await ctx.message.channel.pins()
        last_pin = pins[0]
        print(last_pin)
        await last_pin.delete()
    else: 
        await ctx.message.pin()


# Git command
@bot.command(pass_context=True)
async def git(ctx, *args): 
    await ctx.message.channel.send('https://github.com/JavaCafe01/mikasa')

# Poll command
@bot.command(pass_context=True)
async def poll(ctx, *args):
    content_str = ctx.message.content.replace('-poll', '').strip()
    embedVar = discord.Embed(title='Poll by {}'.format(
        ctx.message.author.display_name),
            description=content_str,
            color=0x824946)
    msg = await ctx.message.channel.send(embed=embedVar)
    await msg.add_reaction(yes_emoji)
    await msg.add_reaction(maybe_emoji)
    await msg.add_reaction(no_emoji)


# Ping command
@bot.command(pass_context=True)
async def ping(ctx, *args):
    a = ctx.message.content.replace('-ping', '').strip()
    #a = a.replace("<","")
    #a = a.replace(">","")
    #a = a.replace("@","")
    #embedVar = discord.Embed(title=a + ' Humanity needs you! Get on the server.', color=0x824946)
    await ctx.message.channel.send(a + ' Humanity needs you! Get on the server')


# Swear jar command
@bot.command(pass_context=True)
async def sjar(ctx, *args):
    embedVar = discord.Embed(title='Swear Jar', color=0x824946)
    sorted_d = sorted((value, key) for (key,value) in swear_rank.items())
    for tup in sorted_d:
        rank = tup[1] + "\t" + str(tup[0])
        embedVar.add_field(name=rank, value="-------------------", inline=False)
    await ctx.message.channel.send(embed=embedVar)



# --{{{ Stuff that listens to all messages
# ---{ Reaction Helper
async def react_message(key, message, emoji):
    if key in message.content.lower():
        await message.add_reaction(emoji)
# ---}


async def swear_listener(message):
    bad_words = ["fuck", "retard", "bitch", "men are trash"]

    for word in bad_words:
        if message.content.lower().count(word) > 0:
            auth = message.author.display_name
            swear_rank[auth] = swear_rank.get(auth, 0) + 1
            print(swear_rank)
            await message.channel.purge(limit=1)
            await message.channel.send('Please refrain from using bad language, {}'.format(auth))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Add reactions
    await react_message("historia", message, bot.get_emoji(anger_emoji))
    await react_message("levi", message, knife_emoji)
    await react_message("eren", message, bot.get_emoji(creepy_annie_emoji))

    # Listen for swearing
    await swear_listener(message)

    # Listen for no u's
    if 'no u' in message.content.lower():
        await message.add_reaction(bot.get_emoji(mikasa_ded_emoji))

    # Listen for compliments
    if "mikasa" in message.content.lower():
        if "cool" in message.content.lower() or \
                "good" in message.content.lower():
            await message.channel.send("> " + message.content + "\n" + 
                    message.author.mention, file=discord.File(mikasa_scarf_gif))
        if "sucks" in message.content.lower() or \
                "sux" in message.content.lower() or \
                "bad" in message.content.lower():
            await message.channel.send("> " + message.content + "\n" + 
                    message.author.mention, file=discord.File(mikasa_stare_gif))    
    await bot.process_commands(message)
# --}}}


# Run on start
@bot.event
async def on_ready():
    print('Bot logged in as {0.user}'.format(bot))

bot.add_cog(Music(bot))
bot.run(TOKEN)

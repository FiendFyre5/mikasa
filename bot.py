#!/usr/bin/env python

# Imports
import os
import discord

from discord.ext import commands
from dotenv import load_dotenv
from discord.utils import get

from mikajam import Mikajam


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
                   description='Simple Bot')


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
            await message.channel.send('> Please refrain from using bad language, {}'.format(auth))


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

    
    # Clear cache of youtubes
    if 'clear cache' in message.content.lower():
        os.system("rm -f youtube-*")
        await message.channel.send("> Youtube cache cleared " + 
                message.author.mention)


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

bot.add_cog(Mikajam(bot))
bot.run(TOKEN)

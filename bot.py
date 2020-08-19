#!/usr/bin/env python

# Imports
import os

import discord
from dotenv import load_dotenv

import io
import aiohttp

# Load token and guild name from env vars
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

client = discord.Client()

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
anger_emoji = client.get_emoji(736335946060136480)
mikasa_ded_emoji = client.get_emoji(745556147376881714)
knife_emoji = "\U0001f5e1"

# --{{{ Reaction Helper
async def react_message(key, message, emoji):
    if key in message.content.lower():
        await message.add_reaction(emoji)
# ---}}}

async def send_git_link(message):
    if message.content == '-git':
        embedVar = discord.Embed(title='Git Repository',
                url='https://www.youtube.com/',
                color=0x824946)
        await message.channel.send(embed=embedVar)




@client.event
async def on_ready():
    print('Bot logged in as {0.user}'.format(client))


@client.event
async def on_message(message):



    if message.author == client.user:
        return

    if message.content == '-hello':
        await message.channel.send('EREN!')

    # Add reactions here
    await react_message("historia", message, mikasa_ded_emoji)
    await react_message("levi", message, knife_emoji)

    if 'no u' in message.content.lower():
        await message.add_reaction(mikasa_ded_emoji)

    if "mikasa" in message.content.lower():
        if "cool" in message.content.lower():
            await message.channel.send(file=discord.File(mikasa_scarf_gif))
        if "sucks" in message.content.lower() or \
                "sux" in message.content.lower() or \
                "bad" in message.content.lower(): 
            await message.channel.send(file=discord.File(mikasa_stare_gif))

    send_git_link(message)

client.run(TOKEN)

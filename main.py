import asyncio
import json
import os
import aiohttp
import discord

from dotenv import load_dotenv
from discord.ext import commands

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    trusted_guilds = general_config["trusted_guilds"]
# ====================================================

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix=['♪','&'],intents=intents, help_command=None)


@bot.event
async def on_ready():
    print('Ready!')

for filename in os.listdir('./cogs'):
    if filename.endswith('.py') and not filename.startswith("nocog"):
        bot.load_extension(f'cogs.{filename[:-3]}')

bot.run(os.getenv('BOT_TOKEN'))
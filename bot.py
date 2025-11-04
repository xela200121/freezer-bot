# main.py
"""Entry point principale del bot"""

import discord
from discord.ext import commands
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TOKEN
from commands import BotCommands
from events import BotEvents
from web_server import WebServer


async def main():
    """Funzione principale asincrona per avviare il bot"""
    
    # Configurazione bot
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    # Scheduler per notifiche
    scheduler = AsyncIOScheduler()
    
    # Setup comandi ed eventi
    BotCommands.setup_commands(bot)
    BotEvents.setup_events(bot, scheduler)
    
    # Avvia web server in background
    asyncio.create_task(WebServer.start_web_server())
    
    # Avvia il bot
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("🛑 Arresto manuale del bot...")
    finally:
        await bot.close()
        print("✅ Bot chiuso correttamente.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Interruzione da tastiera")
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


def main():
    """Funzione principale per avviare il bot"""
    
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
    
    # Avvio
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(WebServer.start_web_server())  # Avvia il web server in parallelo
        loop.create_task(bot.start(TOKEN))    # Avvia il bot
        loop.run_forever()
    except KeyboardInterrupt:
        print("🛑 Arresto manuale del bot...")
    finally:
        loop.run_until_complete(bot.close())
        print("✅ Bot chiuso correttamente.")


if __name__ == "__main__":
    main()

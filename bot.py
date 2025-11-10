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

# Configurazione intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Inizializza bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Inizializza scheduler
scheduler = AsyncIOScheduler()


@bot.event
async def on_ready():
    """Evento quando il bot si connette"""
    from notifications import NotificationManager
    
    print(f'✅ Bot connesso come {bot.user}')
    print(f'ID: {bot.user.id}')
    print('-------------------')
    
    # Sincronizza i comandi slash
    try:
        synced = await bot.tree.sync()
        print(f'✅ Sincronizzati {len(synced)} comandi')
    except Exception as e:
        print(f'❌ Errore sincronizzazione comandi: {e}')
    
    # Avvia scheduler per notifiche
    if not scheduler.running:
        # ========== JOB 1: PREPARA NOTIFICHE GIORNALIERE ==========
        # Esegue ogni giorno a mezzanotte e 1 minuto
        scheduler.add_job(
            lambda: asyncio.create_task(NotificationManager.prepara_notifiche_giornaliere(bot)),
            'cron',
            hour=0,
            minute=1,
            id='prepara_notifiche',
            replace_existing=True
        )
        print('✅ Job "prepara_notifiche" schedulato: ogni giorno alle 00:01')
        
        # ========== JOB 2: ELABORA CODA NOTIFICHE ==========
        # Esegue ogni minuto per elaborare la coda
        scheduler.add_job(
            lambda: asyncio.create_task(NotificationManager.elabora_coda_notifiche(bot)),
            'interval',
            minutes=1,
            id='elabora_coda',
            replace_existing=True
        )
        print('✅ Job "elabora_coda" schedulato: ogni 1 minuto')
        
        # ========== JOB 3: PULIZIA NOTIFICHE VECCHIE ==========
        # Esegue ogni giorno alle 2:00 di notte
        scheduler.add_job(
            lambda: asyncio.create_task(NotificationManager.pulisci_notifiche_vecchie()),
            'cron',
            hour=2,
            minute=0,
            id='pulizia_notifiche',
            replace_existing=True
        )
        print('✅ Job "pulizia_notifiche" schedulato: ogni giorno alle 02:00')
        
        # Avvia lo scheduler
        scheduler.start()
        print('✅ Scheduler avviato')
        
        # ========== IMPORTANTE: Prepara notifiche per OGGI al primo avvio ==========
        print('🔄 Esecuzione iniziale: preparazione notifiche per oggi...')
        await NotificationManager.prepara_notifiche_giornaliere(bot)
        print('✅ Preparazione iniziale completata')
    
    # Imposta stato del bot
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="il tuo freezer 🧊 | /menu"
        )
    )


async def main():
    """Funzione principale per avviare bot e web server"""
    # Registra comandi ed eventi
    BotCommands.setup_commands(bot)
    BotEvents.setup_events(bot, scheduler)
    
    # Avvia web server in background (UNA VOLTA SOLA!)
    asyncio.create_task(WebServer.start_web_server())
    
    # Avvia il bot
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Bot fermato manualmente")
    finally:
        if scheduler.running:
            scheduler.shutdown()
        await bot.close()
        print("✅ Bot chiuso correttamente.")


if __name__ == "__main__":
    asyncio.run(main())
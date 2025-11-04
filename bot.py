# main.py
import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TOKEN, PORT, BOT_PREFIX
from services.thread_service import ThreadService
from services.notification_service import NotificationService
from services.display_service import DisplayService
from commands.slash_commands import SlashCommands
from utils.helpers import start_web_server


class FreezerBot:
    """Classe principale del bot"""
    
    def __init__(self):
        # Configurazione intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Crea il bot
        self.bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)
        
        # Inizializza servizi
        self.notification_service = NotificationService(self.bot)
        self.display_service = DisplayService(self.notification_service)
        self.thread_service = ThreadService(self.display_service)
        
        # Scheduler per notifiche
        self.scheduler = AsyncIOScheduler()
        
        # Registra eventi e comandi
        self._register_events()
        
        # Inizializza comandi slash
        self.slash_commands = SlashCommands(
            self.bot, 
            self.display_service, 
            self.thread_service
        )
        self.slash_commands.register_commands()
    
    def _register_events(self):
        """Registra tutti gli eventi del bot"""
        
        @self.bot.event
        async def on_ready():
            """Evento quando il bot si connette"""
            print(f'✅ Bot connesso come {self.bot.user}')
            print(f'ID: {self.bot.user.id}')
            print('-------------------')
            
            # Sincronizza i comandi slash
            try:
                synced = await self.bot.tree.sync()
                print(f'✅ Sincronizzati {len(synced)} comandi')
            except Exception as e:
                print(f'❌ Errore sincronizzazione comandi: {e}')
            
            # Avvia scheduler per notifiche
            if not self.scheduler.running:
                self.scheduler.add_job(
                    self.notification_service.controlla_reminder, 
                    'interval', 
                    minutes=60
                )
                self.scheduler.start()
                print('✅ Scheduler notifiche avviato')
            
            # Imposta stato del bot
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="il tuo freezer 🧊 | /menu"
                )
            )
        
        @self.bot.event
        async def on_member_join(member):
            """Evento quando un nuovo utente entra nel server"""
            print(f"👋 Nuovo membro: {member.name} (ID: {member.id})")
            
            # Ignora i bot
            if member.bot:
                print(f"🤖 {member.name} è un bot, lo ignoro")
                return
            
            try:
                # Crea il thread privato per l'utente
                thread = await self.thread_service.crea_thread_utente(member.guild, member)
                
                if thread:
                    print(f"✅ Thread creato con successo per {member.name}")
                else:
                    print(f"⚠️ Impossibile creare thread per {member.name}")
                    
            except Exception as e:
                print(f"❌ Errore nella gestione del nuovo membro {member.name}: {e}")
        
        @self.bot.event
        async def on_command_error(ctx, error):
            """Gestisce errori nei comandi"""
            if isinstance(error, commands.CommandNotFound):
                return
            print(f'Errore: {error}')
    
    async def start_web_server(self):
        """Avvia un semplice web server per Render"""
        async def health_check(request):
            """Endpoint per health check di Render"""
            return web.Response(text="Bot is running!")
        
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        print(f'✅ Web server avviato sulla porta {PORT}')
    
    async def start(self):
        """Avvia il bot e il web server"""
        try:
            # Avvia web server in parallelo
            asyncio.create_task(self.start_web_server())
            # Avvia il bot
            await self.bot.start(TOKEN)
        except KeyboardInterrupt:
            print("🛑 Arresto manuale del bot...")
        finally:
            await self.bot.close()
            print("✅ Bot chiuso correttamente.")


def main():
    """Entry point dell'applicazione"""
    freezer_bot = FreezerBot()
    
    try:
        asyncio.run(freezer_bot.start())
    except KeyboardInterrupt:
        print("🛑 Arresto manuale del bot...")


if __name__ == "__main__":
    main()

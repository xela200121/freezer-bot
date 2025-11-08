# events.py
"""Eventi del bot Discord"""

import discord
from discord.ext import commands
from thread_manager import ThreadManager


class BotEvents:
    """Classe per gestire gli eventi del bot"""
    
    @staticmethod
    def setup_events(bot, scheduler):
        """Registra tutti gli eventi del bot"""
        
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
                scheduler.add_job(
                    lambda: NotificationManager.controlla_reminder(bot), 
                    'interval', 
                    minutes=5
                )
                scheduler.start()
                print('✅ Scheduler notifiche avviato')
            
            # Imposta stato del bot
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="il tuo freezer 🧊 | /menu"
                )
            )
        
        @bot.event
        async def on_member_join(member):
            """Evento quando un nuovo utente entra nel server"""
            print(f"👋 Nuovo membro: {member.name} (ID: {member.id})")
            
            # Ignora i bot
            if member.bot:
                print(f"🤖 {member.name} è un bot, lo ignoro")
                return
            
            try:
                # Crea il thread privato per l'utente
                thread = await ThreadManager.crea_thread_utente(member.guild, member)
                
                if thread:
                    print(f"✅ Thread creato con successo per {member.name}")
                else:
                    print(f"⚠️ Impossibile creare thread per {member.name}")
                    
            except Exception as e:
                print(f"❌ Errore nella gestione del nuovo membro {member.name}: {e}")
        
        @bot.event
        async def on_command_error(ctx, error):
            """Gestisce errori nei comandi"""
            if isinstance(error, commands.CommandNotFound):
                return
            print(f'Errore: {error}')

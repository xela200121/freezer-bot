# events.py
"""Eventi del bot Discord"""

import discord
from discord.ext import commands
from thread_manager import ThreadManager


class BotEvents:
    """Classe per gestire gli eventi del bot"""
    
    @staticmethod
    def setup_events(bot, scheduler):
        """
        Registra gli eventi del bot.
        
        NOTA: on_ready è definito in bot.py/main.py per gestire lo scheduler.
        Qui registriamo solo on_member_join e on_command_error.
        """
        
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
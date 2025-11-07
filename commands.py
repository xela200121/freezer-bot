# commands.py
"""Comandi slash del bot"""

import discord
from discord import app_commands
from ui_handlers import UIHandlers
from database import DatabaseManager
from thread_manager import ThreadManager


class BotCommands:
    """Classe per gestire i comandi del bot"""
    
    @staticmethod
    def setup_commands(bot):
        """Registra tutti i comandi slash"""
        
        @bot.tree.command(name="menu", description="Mostra il menu principale di FreezerBot")
        async def menu_command(interaction: discord.Interaction):
            """Comando /menu per aprire il menu principale"""
            await UIHandlers.mostra_menu_principale(interaction)
        
        @bot.tree.command(name="lista", description="Mostra tutti gli alimenti nel freezer")
        async def lista_command(interaction: discord.Interaction):
            """Comando /lista per vedere gli alimenti"""
            await UIHandlers.mostra_lista(interaction)
        
        @bot.tree.command(name="aggiungi", description="Aggiungi alimenti o porzioni")
        async def aggiungi_command(interaction: discord.Interaction):
            """Comando /aggiungi"""
            await UIHandlers.mostra_menu_aggiungi(interaction)
        
        @bot.tree.command(name="help", description="Guida all'uso di FreezerBot")
        async def help_command(interaction: discord.Interaction):
            """Comando /help"""
            embed = discord.Embed(
                title="📚 Guida FreezerBot",
                description="Ecco come usare il bot per gestire il tuo freezer!",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🎯 Comandi Principali",
                value="`/menu` - Apri il menu principale\n"
                      "`/lista` - Vedi tutti gli alimenti\n"
                      "`/aggiungi` - Aggiungi alimenti",
                inline=False
            )
            
            embed.add_field(
                name="📢 Come funzionano i promemoria?",
                value="Il bot ti invierà un messaggio privato il giorno e l'ora che scegli "
                      "per ricordarti di tirare fuori l'alimento dal freezer!",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Notifica quantità finita",
                value="Quando la quantità arriva a 1, riceverai una notifica con "
                      "i grammi da comprare per quel giorno della settimana.",
                inline=False
            )
            
            embed.add_field(
                name="💡 Suggerimenti",
                value="• Puoi avere più varianti dello stesso alimento per giorni diversi\n"
                      "• Usa i bottoni per aggiungere/rimuovere porzioni velocemente\n"
                      "• Abilita/disabilita le notifiche dalle impostazioni",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @bot.tree.command(name="crea_mio_thread", description="[ADMIN] Crea il tuo thread personale per il freezer")
        @app_commands.checks.has_permissions(administrator=True)
        async def crea_mio_thread_command(interaction: discord.Interaction):
            """Permette a un admin di creare il proprio thread"""
            await interaction.response.defer(ephemeral=True)
            
            # Controlla se l'admin ha già un thread
            thread_esistente = DatabaseManager.get_user_thread(interaction.guild.id, interaction.user.id)
            
            if thread_esistente:
                # Prova a recuperare il thread
                try:
                    thread = interaction.guild.get_thread(int(thread_esistente['thread_id']))
                    if thread:
                        await interaction.followup.send(
                            f"✅ Hai già un thread attivo: {thread.mention}",
                            ephemeral=True
                        )
                        return
                except:
                    # Thread non trovato, ne creiamo uno nuovo
                    pass
            
            # Crea il thread per l'admin
            thread = await ThreadManager.crea_thread_utente(interaction.guild, interaction.user)
            
            if thread:
                await interaction.followup.send(
                    f"✅ Thread personale creato con successo: {thread.mention}\n"
                    f"Usa `/menu` per iniziare a gestire il tuo freezer!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Errore nella creazione del thread. Controlla i permessi del bot.",
                    ephemeral=True
                )
        
        @crea_mio_thread_command.error
        async def crea_mio_thread_error(interaction: discord.Interaction, error):
            """Gestisce errori di permessi"""
            if isinstance(error, app_commands.errors.MissingPermissions):
                await interaction.response.send_message(
                    "❌ Solo gli amministratori possono usare questo comando!",
                    ephemeral=True
                )

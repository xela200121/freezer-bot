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

        @bot.tree.command(name="pulisci", description="Cancella tutti i messaggi nel thread (escluso il menu principale)")
        async def pulisci_command(interaction: discord.Interaction):
            """Comando per pulire la cronologia del thread"""
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Verifica che siamo in un thread
                if not isinstance(interaction.channel, discord.Thread):
                    await interaction.followup.send(
                        "⚠️ Questo comando funziona solo nei thread privati!",
                        ephemeral=True
                    )
                    return
                
                # Verifica che sia il thread dell'utente
                thread_data = DatabaseManager.get_user_thread(interaction.guild.id, interaction.user.id)
                if not thread_data or str(interaction.channel.id) != thread_data['thread_id']:
                    await interaction.followup.send(
                        "⚠️ Puoi usare questo comando solo nel tuo thread personale!",
                        ephemeral=True
                    )
                    return
                
                # Conta e elimina i messaggi
                deleted_count = 0
                async for message in interaction.channel.history(limit=100):
                    # Non eliminare il messaggio di benvenuto e il menu principale
                    if message.author == interaction.client.user:
                        # Controlla se ha il menu principale (view con bottoni)
                        if message.components:
                            continue
                    
                    try:
                        await message.delete()
                        deleted_count += 1
                    except discord.Forbidden:
                        continue
                    except discord.NotFound:
                        continue
                
                await interaction.followup.send(
                    f"🧹 Thread pulito! Eliminati **{deleted_count}** messaggi.",
                    ephemeral=True
                )
                
            except Exception as e:
                print(f"Errore pulizia thread: {e}")
                await interaction.followup.send(
                    "❌ Errore durante la pulizia del thread.",
                    ephemeral=True
                )


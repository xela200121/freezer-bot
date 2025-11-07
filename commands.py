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

        @bot.tree.command(name="reset", description="Resetta completamente il thread (elimina e ricrea)")
        async def reset_command(interaction: discord.Interaction):
            """Comando per resettare il thread completamente"""
            print("🔴 COMANDO RESET AVVIATO")
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Verifica che siamo in un thread
                if not isinstance(interaction.channel, discord.Thread):
                    await interaction.followup.send(
                        "⚠️ Questo comando funziona solo nei thread privati!",
                        ephemeral=True
                    )
                    return
                
                print(f"✅ È un thread: {interaction.channel.name}")
                thread_name = interaction.channel.name
                channel = interaction.channel.parent
                user = interaction.user
                guild = interaction.guild
                
                # Archivia il thread vecchio
                try:
                    print("🔄 Archiviando thread vecchio...")
                    await interaction.channel.edit(archived=True)
                    print("✅ Thread archiviato")
                except Exception as e:
                    print(f"⚠️ Errore nell'archiviare thread: {e}")
                
                # Crea un nuovo thread con lo stesso nome
                print("🔄 Creando nuovo thread...")
                new_thread = await channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread
                )
                print(f"✅ Nuovo thread creato: {new_thread.id}")
                
                # Aggiorna il database con il nuovo thread ID
                print("🔄 Aggiornando database...")
                DatabaseManager.save_user_thread(guild.id, user.id, channel.id, new_thread.id)
                print("✅ Database aggiornato")
                
                # Invia il messaggio di benvenuto nel nuovo thread
                print("🔄 Inviando messaggio di benvenuto...")
                await ThreadManager._invia_messaggio_benvenuto(new_thread, user)
                print("✅ Messaggio di benvenuto inviato")
                
                # Notifica l'utente nel vecchio thread
                await interaction.followup.send(
                    f"♻️ Thread resettato! Vai al nuovo thread: {new_thread.mention}",
                    ephemeral=True
                )
                
                print(f"✅ RESET COMPLETATO")
                
            except Exception as e:
                print(f"❌ ERRORE CRITICO: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                
                try:
                    await interaction.followup.send(
                        f"❌ Errore durante il reset: {str(e)}",
                        ephemeral=True
                    )
                except:
                    print("❌ Impossibile inviare messaggio di errore")

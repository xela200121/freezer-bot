# thread_manager.py
"""Gestione thread privati per gli utenti"""

import discord
from database import DatabaseManager
from config import NOME_CANALE_LISTA_SPESA


class ThreadManager:
    """Manager per la creazione e gestione dei thread privati"""
    
    @staticmethod
    async def crea_thread_utente(guild, member):
        """Crea o recupera il thread privato per un utente"""
        try:
            # Cerca il canale #lista-spesa
            canale = discord.utils.get(guild.text_channels, name=NOME_CANALE_LISTA_SPESA)
            
            # Se non esiste, crealo
            if not canale:
                print(f"📝 Creazione canale #{NOME_CANALE_LISTA_SPESA}...")
                canale = await guild.create_text_channel(
                    NOME_CANALE_LISTA_SPESA,
                    topic="📋 Canale per le liste della spesa personali",
                    reason="Creato automaticamente da FreezerBot"
                )
                print(f"✅ Canale #{NOME_CANALE_LISTA_SPESA} creato!")
            
            # Controlla se l'utente ha già un thread
            thread_data = DatabaseManager.get_user_thread(guild.id, member.id)
            
            if thread_data:
                # Prova a recuperare il thread esistente
                try:
                    thread = guild.get_thread(int(thread_data['thread_id']))
                    if thread:
                        print(f"♻️ Thread esistente trovato per {member.name}")
                        return thread
                except:
                    print(f"⚠️ Thread salvato non trovato, ne creo uno nuovo")
            
            # Crea un nuovo thread privato
            nome_thread = f"🧊 Freezer di {member.display_name}"
            
            thread = await canale.create_thread(
                name=nome_thread,
                type=discord.ChannelType.private_thread,
                reason=f"Thread privato per {member.name}",
                invitable=False
            )
            
            print(f"✅ Thread privato creato per {member.name}")
            
            # Salva il thread nel database
            DatabaseManager.save_user_thread(guild.id, member.id, canale.id, thread.id)
            
            # Invita l'utente nel thread
            await thread.add_user(member)
            print(f"✅ {member.name} aggiunto al thread")
            
            # Invia messaggio di benvenuto
            await ThreadManager._invia_messaggio_benvenuto(thread, member)
            
            return thread
            
        except discord.Forbidden:
            print(f"❌ Permessi insufficienti per creare thread in {guild.name}")
            return None
        except Exception as e:
            print(f"❌ Errore nella creazione del thread: {e}")
            return None
    
    @staticmethod
    async def _invia_messaggio_benvenuto(thread, member):
        """Invia il messaggio di benvenuto nel thread"""
        # Import qui per evitare circular import
        from views import MenuPrincipale
        
        embed = discord.Embed(
            title=f"👋 Benvenuto nel tuo Freezer personale, {member.display_name}!",
            description="Questo è il tuo spazio privato per gestire il congelatore.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Cosa puoi fare qui",
            value="• Gestire gli alimenti nel tuo freezer\n"
                  "• Ricevere promemoria per scongelare\n"
                  "• Tenere traccia delle quantità\n"
                  "• Ricevere notifiche quando finiscono gli alimenti",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Come iniziare",
            value="Usa il comando `/menu` per aprire il menu principale!\n"
                  "Oppure usa `/help` per vedere tutti i comandi disponibili.",
            inline=False
        )
        
        embed.add_field(
            name="🔒 Privacy",
            value="Questo thread è **privato**: solo tu e il bot potete vedere i messaggi qui dentro.",
            inline=False
        )
        
        embed.set_footer(text="FreezerBot 🧊 | Il tuo assistente per il congelatore")
        
        await thread.send(embed=embed)
        
        # Invia anche il menu principale
        await thread.send("Ecco il tuo menu principale:")
        
        menu_embed = discord.Embed(
            title="🧊 FreezerBot",
            description="Gestisci il tuo congelatore facilmente!",
            color=discord.Color.blue()
        )
        menu_embed.add_field(
            name="📋 Lista",
            value="Vedi tutti gli alimenti",
            inline=False
        )
        menu_embed.add_field(
            name="➕ Aggiungi",
            value="Aggiungi alimenti o porzioni",
            inline=False
        )
        menu_embed.add_field(
            name="⚙️ Impostazioni",
            value="Modifica reminder e notifiche",
            inline=False
        )
        
        view = MenuPrincipale()
        await thread.send(embed=menu_embed, view=view)

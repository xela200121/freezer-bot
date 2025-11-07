# ui_handlers.py
"""Handler per la visualizzazione degli embed e menu"""

import discord
from database import DatabaseManager
from config import GIORNI
from views import (MenuPrincipale, ListaAlimentiView, GestioneAlimentoView,
                   AggiungiAlimentoView, ModificaAlimentiView, ModificaAlimentoView,
                   SelezioneGiornoView, SelezioneOrarioView)


class UIHandlers:
    """Handler per gestire la UI e la visualizzazione"""
    
    @staticmethod
    async def mostra_menu_principale(interaction: discord.Interaction):
        """Mostra il menu principale"""
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        embed = discord.Embed(
            title="🧊 FreezerBot",
            description="Gestisci il tuo congelatore facilmente!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Lista",
            value="Vedi tutti gli alimenti",
            inline=False
        )
        embed.add_field(
            name="➕ Aggiungi",
            value="Aggiungi alimenti o porzioni",
            inline=False
        )
        embed.add_field(
            name="⚙️ Modifica alimenti",
            value="Modifica reminder e notifiche",
            inline=False
        )
        
        view = MenuPrincipale()
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @staticmethod
    async def mostra_lista(interaction: discord.Interaction):
        """Mostra la lista degli alimenti"""
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        alimenti = DatabaseManager.get_alimenti_utente(interaction.user.id)
        
        if not alimenti:
            embed = discord.Embed(
                title="🧊 Il Tuo Freezer",
                description="Il freezer è vuoto! Usa **➕ Aggiungi** per iniziare.",
                color=discord.Color.blue()
            )
            view = MenuPrincipale()
        else:
            embed = discord.Embed(
                title="🧊 Il Tuo Freezer",
                description=f"Hai **{len(alimenti)}** alimenti salvati:",
                color=discord.Color.blue()
            )
            
            # Raggruppa per giorno
            for giorno_num in sorted(set([a['scongela_per_giorno'] for a in alimenti])):
                alimenti_giorno = [a for a in alimenti if a['scongela_per_giorno'] == giorno_num]
                testo = "\n".join([
                    f"• **{a['nome_alimento'].capitalize()}**: {a['quantita']} {a.get('unita', 'pz')}"
                    for a in alimenti_giorno
                ])
                embed.add_field(
                    name=f"📅 {GIORNI[giorno_num]}",
                    value=testo,
                    inline=False
                )
            
            view = ListaAlimentiView(alimenti, interaction.user.id)
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @staticmethod
    async def mostra_gestione_alimento(interaction: discord.Interaction, id_univoco: str):
        """Mostra la gestione di un singolo alimento"""
        alimento = DatabaseManager.get_alimento_by_id(interaction.user.id, id_univoco)
        
        if not alimento:
            await interaction.edit_original_response(content="❌ Alimento non trovato!")
            return
        
        embed = UIHandlers.crea_embed_alimento(alimento)
        view = GestioneAlimentoView(alimento, interaction.user.id)
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @staticmethod
    def crea_embed_alimento(alimento):
        """Crea embed per singolo alimento"""
        embed = discord.Embed(
            title=f"🍖 {alimento['nome_alimento'].capitalize()}",
            color=discord.Color.green() if alimento['quantita'] > 0 else discord.Color.red()
        )
        embed.add_field(
            name="📦 Quantità",
            value=f"{alimento['quantita']} {alimento.get('unita', 'pz')}",
            inline=True
        )
        embed.add_field(
            name="📅 Per il giorno",
            value=GIORNI[alimento['scongela_per_giorno']],
            inline=True
        )
        embed.add_field(
            name="📢 Reminder",
            value=f"{GIORNI[alimento['reminder_day']]} alle {alimento['reminder_hours']}",
            inline=True
        )
        embed.add_field(
            name="🛒 Da comprare",
            value=f"{alimento['portion_to_buy']}g",
            inline=True
        )
        embed.add_field(
            name="Notifiche",
            value="✅ Attive" if alimento['notifiche_abilitate'] else "❌ Disattivate",
            inline=True
        )
        
        return embed
    
    @staticmethod
    async def mostra_menu_aggiungi(interaction: discord.Interaction):
        """Mostra menu per aggiungere alimenti"""
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        embed = discord.Embed(
            title="➕ Aggiungi Alimento",
            description="Scegli se aggiungere porzioni a un alimento esistente o crearne uno nuovo.",
            color=discord.Color.green()
        )
        
        view = AggiungiAlimentoView(interaction.user.id)
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @staticmethod
    async def mostra_selezione_variante(interaction: discord.Interaction, nome: str, alimenti: list):
        """Mostra selezione tra più varianti dello stesso alimento"""
        options = []
        for alimento in alimenti[:25]:
            label = f"{GIORNI[alimento['scongela_per_giorno']]} - {alimento['portion_to_buy']}g"
            options.append(discord.SelectOption(
                label=label,
                value=alimento['id_univoco']
            ))
        
        select = discord.ui.Select(
            placeholder=f"Quale {nome} vuoi incrementare?",
            options=options
        )
        
        async def callback(inter):
            await inter.response.defer()
            id_univoco = inter.data['values'][0]
            DatabaseManager.aggiorna_quantita(interaction.user.id, id_univoco, 1)
            await inter.edit_original_response(
                content=f"✅ Aggiunta 1 porzione di **{nome}**!",
                view=None
            )
        
        select.callback = callback
        view = discord.ui.View()
        view.add_item(select)
        
        await interaction.edit_original_response(
            content=f"Hai più varianti di **{nome}**. Quale vuoi incrementare?",
            view=view
        )
    
    @staticmethod
    async def mostra_selezione_giorno(interaction: discord.Interaction, nome: str, quantita: int, portion_to_buy: int):
        """Mostra menu per selezionare il giorno"""
        embed = discord.Embed(
            title="📅 Seleziona Giorno",
            description=f"Per quale giorno vuoi scongelare **{nome.capitalize()}**?",
            color=discord.Color.blue()
        )
        
        view = SelezioneGiornoView(nome, quantita, portion_to_buy, interaction.user.id)
        await interaction.edit_original_response(embed=embed, view=view)
    
    @staticmethod
    async def mostra_selezione_orario(interaction: discord.Interaction, nome: str, quantita: int, portion_to_buy: int, giorno: int):
        """Mostra menu per selezionare l'orario"""
        from models import AlimentoHelper
        reminder_day = AlimentoHelper.calcola_reminder_day(giorno)
        
        embed = discord.Embed(
            title="🕐 Seleziona Orario",
            description=f"A che ora vuoi ricevere il promemoria per **{nome.capitalize()}**?\n(Il giorno prima: {GIORNI[reminder_day]})",
            color=discord.Color.blue()
        )
        
        view = SelezioneOrarioView(nome, quantita, portion_to_buy, giorno, interaction.user.id)
        await interaction.edit_original_response(embed=embed, view=view)
    
    @staticmethod
    async def mostra_modifica_alimenti(interaction: discord.Interaction):
        """Mostra menu impostazioni"""
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        alimenti = DatabaseManager.get_alimenti_utente(interaction.user.id)
        
        if not alimenti:
            embed = discord.Embed(
                title="⚙️ Modifica alimenti",
                description="Non hai ancora alimenti da configurare!",
                color=discord.Color.orange()
            )
            view = MenuPrincipale()
        else:
            embed = discord.Embed(
                title="⚙️ Modifica alimenti",
                description="Seleziona un alimento da modificare:",
                color=discord.Color.blue()
            )
            view = ModificaAlimentiView(interaction.user.id)
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @staticmethod
    async def mostra_menu_modifica(interaction: discord.Interaction, alimento: dict):
        """Mostra menu per modificare un alimento"""
        embed = discord.Embed(
            title=f"⚙️ Modifica {alimento['nome_alimento'].capitalize()}",
            description="Cosa vuoi modificare?",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Impostazioni attuali",
            value=f"📅 Giorno: **{GIORNI[alimento['scongela_per_giorno']]}**\n"
                  f"🕐 Orario: **{alimento['reminder_hours']}**\n"
                  f"🔔 Notifiche: **{'Attive' if alimento['notifiche_abilitate'] else 'Disattivate'}**\n"
                  f"🛒 Da comprare: **{alimento['portion_to_buy']}g**",
            inline=False
        )
        
        view = ModificaAlimentoView(alimento, interaction.user.id)
        
        await interaction.edit_original_response(embed=embed, view=view)

# views.py
"""Classi View per bottoni e menu interattivi"""

import discord
from discord import ui
from database import DatabaseManager
from config import GIORNI
from models import AlimentoHelper


class MenuPrincipale(ui.View):
    """Menu principale con pulsanti Lista, Aggiungi, Modifica alimenti"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="📋 Lista", style=discord.ButtonStyle.primary, custom_id="lista")
    async def lista_button(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_lista(interaction)
    
    @ui.button(label="➕ Aggiungi", style=discord.ButtonStyle.green, custom_id="aggiungi")
    async def aggiungi_button(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_menu_aggiungi(interaction)



class ListaAlimentiView(ui.View):
    """View per gestire la lista alimenti con bottoni +/-"""
    def __init__(self, alimenti, user_id):
        super().__init__(timeout=180)
        self.alimenti = alimenti
        self.user_id = user_id
        
        # Aggiungi select menu per scegliere l'alimento
        options = []
        for alimento in alimenti[:25]:  # Max 25 opzioni
            label = f"{alimento['nome_alimento']} - {alimento['quantita']} {alimento.get('unita', 'pz')}"
            options.append(discord.SelectOption(
                label=label,
                value=alimento['id_univoco'],
                description=f"Per {GIORNI[alimento['scongela_per_giorno']]}"
            ))
        
        if options:
            select = ui.Select(
                placeholder="Seleziona un alimento da gestire",
                options=options,
                custom_id="select_alimento"
            )
            select.callback = self.select_callback
            self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        from ui_handlers import UIHandlers
        id_univoco = interaction.data['values'][0]
        await interaction.response.defer()
        await UIHandlers.mostra_gestione_alimento(interaction, id_univoco)
    
    @ui.button(label="🏠 Menu", style=discord.ButtonStyle.secondary, row=4)
    async def menu_button(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_menu_principale(interaction)


class GestioneAlimentoView(ui.View):
    """View per gestire singolo alimento (+1, -1, Rimuovi)"""
    def __init__(self, alimento, user_id):
        super().__init__(timeout=180)
        self.alimento = alimento
        self.user_id = user_id
        self.id_univoco = alimento['id_univoco']
    
    @ui.button(label="➕ Aggiungi 1", style=discord.ButtonStyle.green)
    async def aggiungi_uno(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        nuova_quantita = DatabaseManager.aggiorna_quantita(self.user_id, self.id_univoco, 1)
        self.alimento['quantita'] = nuova_quantita
        await interaction.edit_original_response(
            embed=UIHandlers.crea_embed_alimento(self.alimento),
            view=self
        )
    
    @ui.button(label="➖ Rimuovi 1", style=discord.ButtonStyle.red)
    async def rimuovi_uno(self, interaction: discord.Interaction, button: ui.Button):
        from notifications import NotificationManager
        await interaction.response.defer()
        nuova_quantita = DatabaseManager.aggiorna_quantita(self.user_id, self.id_univoco, -1)
        self.alimento['quantita'] = nuova_quantita
        
        # Notifica se finito
        if nuova_quantita == 1:
            await NotificationManager.notifica_quantita_finita(interaction.user, self.alimento)
        
        from ui_handlers import UIHandlers
        await interaction.edit_original_response(
            embed=UIHandlers.crea_embed_alimento(self.alimento),
            view=self
        )
    
    @ui.button(label="🗑️ Elimina", style=discord.ButtonStyle.danger)
    async def elimina(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        DatabaseManager.rimuovi_alimento(self.user_id, self.id_univoco)
        await interaction.edit_original_response(
            content=f"✅ **{self.alimento['nome_alimento']}** eliminato dal freezer!",
            embed=None,
            view=None
        )
    
    @ui.button(label="⚙️ Modifica", style=discord.ButtonStyle.secondary)
    async def modifica(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_menu_modifica(interaction, self.alimento)
    
    @ui.button(label="◀️ Indietro", style=discord.ButtonStyle.secondary, row=2)
    async def indietro(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_lista(interaction)


class AggiungiAlimentoView(ui.View):
    """View per aggiungere nuovo alimento o porzione esistente"""
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        
        # Ottieni alimenti esistenti
        alimenti = DatabaseManager.get_alimenti_utente(user_id)
        
        if alimenti:
            # Crea set di nomi unici
            nomi_unici = list(set([a['nome_alimento'] for a in alimenti]))
            
            if nomi_unici:
                options = [discord.SelectOption(label=nome.capitalize(), value=nome) 
                          for nome in nomi_unici[:25]]
                
                select = ui.Select(
                    placeholder="Aggiungi porzione a alimento esistente",
                    options=options
                )
                select.callback = self.select_esistente_callback
                self.add_item(select)
    
    async def select_esistente_callback(self, interaction: discord.Interaction):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        nome = interaction.data['values'][0]
        # Mostra gli alimenti con quel nome per scegliere quale incrementare
        alimenti = [a for a in DatabaseManager.get_alimenti_utente(self.user_id) if a['nome_alimento'] == nome]
        
        if len(alimenti) == 1:
            # Solo uno, incrementa direttamente
            DatabaseManager.aggiorna_quantita(self.user_id, alimenti[0]['id_univoco'], 1)
            await interaction.edit_original_response(
                content=f"✅ Aggiunta 1 porzione di **{nome}**!",
                view=None
            )
        else:
            # Più di uno, chiedi quale
            await UIHandlers.mostra_selezione_variante(interaction, nome, alimenti)
    
    @ui.button(label="➕ Nuovo Alimento", style=discord.ButtonStyle.green, row=1)
    async def nuovo_alimento(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(NuovoAlimentoModal())
    
    @ui.button(label="◀️ Indietro", style=discord.ButtonStyle.secondary, row=1)
    async def indietro(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_menu_principale(interaction)


class NuovoAlimentoModal(ui.Modal, title="➕ Aggiungi Nuovo Alimento"):
    """Modal per inserire dati nuovo alimento"""
    
    nome = ui.TextInput(
        label="Nome Alimento",
        placeholder="es: Pollo, Pesce, Verdure...",
        required=True,
        max_length=50
    )
    
    quantita = ui.TextInput(
        label="Quantità",
        placeholder="es: 3",
        required=True,
        max_length=5,
        default="1"
    )
    
    portion_to_buy = ui.TextInput(
        label="Grammi/Porzione da comprare",
        placeholder="es: 150",
        required=True,
        max_length=5,
        default="150"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        # Mostra menu per scegliere giorno
        await UIHandlers.mostra_selezione_giorno(
            interaction,
            self.nome.value,
            int(self.quantita.value),
            int(self.portion_to_buy.value)
        )


class SelezioneGiornoView(ui.View):
    """View per selezionare il giorno di scongelamento"""
    def __init__(self, nome, quantita, portion_to_buy, user_id):
        super().__init__(timeout=180)
        self.nome = nome
        self.quantita = quantita
        self.portion_to_buy = portion_to_buy
        self.user_id = user_id
        
        # Crea select con i giorni
        options = [discord.SelectOption(label=giorno, value=str(num)) 
                  for num, giorno in GIORNI.items()]
        
        select = ui.Select(
            placeholder="In quale giorno mangerai l'alimento "+nome+"?",
            options=options
        )
        select.callback = self.select_giorno_callback
        self.add_item(select)
    
    async def select_giorno_callback(self, interaction: discord.Interaction):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        giorno = int(interaction.data['values'][0])
        await UIHandlers.mostra_selezione_orario(
            interaction,
            self.nome,
            self.quantita,
            self.portion_to_buy,
            giorno
        )


class SelezioneOrarioView(ui.View):
    """View per selezionare orario reminder"""
    def __init__(self, nome, quantita, portion_to_buy, giorno, user_id):
        super().__init__(timeout=180)
        self.nome = nome
        self.quantita = quantita
        self.portion_to_buy = portion_to_buy
        self.giorno = giorno
        self.user_id = user_id
        
        # Crea select con orari
        orari = [f"{h:02d}:00" for h in range(8, 23)]  # Da 08:00 a 22:00
        options = [discord.SelectOption(label=orario, value=orario) for orario in orari]
        
        select = ui.Select(
            placeholder="A che ora vuoi il promemoria?",
            options=options
        )
        select.callback = self.select_orario_callback
        self.add_item(select)
    

    async def select_orario_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            orario = interaction.data['values'][0]
            
            # Crea dizionario alimento
            alimento_dict = AlimentoHelper.crea_alimento_dict(
                self.user_id, self.nome, self.quantita, 
                self.portion_to_buy, self.giorno, orario
            )
            
            # CONTROLLA SE ESISTE GIÀ
            alimento_esistente = DatabaseManager.alimento_esiste(alimento_dict['id_univoco'])
            
            if alimento_esistente:
                # L'alimento esiste già, chiedi conferma
                embed = discord.Embed(
                    title="⚠️ Alimento Esistente!",
                    description=f"Hai già **{self.nome.capitalize()}** per {GIORNI[self.giorno]} con {self.portion_to_buy}g!",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="📦 Quantità attuale",
                    value=f"{alimento_esistente['quantita']} porzioni",
                    inline=True
                )
                embed.add_field(
                    name="➕ Quantità da aggiungere",
                    value=f"{self.quantita} porzioni",
                    inline=True
                )
                embed.add_field(
                    name="📊 Totale",
                    value=f"{alimento_esistente['quantita'] + self.quantita} porzioni",
                    inline=True
                )
                embed.set_footer(text="Vuoi aggiungere la quantità all'alimento esistente?")
                
                view = ConfermaIncrementoView(alimento_esistente, alimento_dict, self.user_id)
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                # Alimento nuovo, inserisci normalmente
                result = DatabaseManager.inserisci_alimento_nuovo(alimento_dict)
                
                if result is None:
                    await interaction.followup.send(
                        content="❌ Errore durante il salvataggio nel database. Riprova!",
                        ephemeral=True
                    )
                    return
                
                reminder_day = AlimentoHelper.calcola_reminder_day(self.giorno)
                
                embed = discord.Embed(
                    title="✅ Alimento Aggiunto!",
                    description=f"**{self.nome.capitalize()}** è stato aggiunto al freezer!",
                    color=discord.Color.green()
                )
                embed.add_field(name="📦 Quantità", value=f"{self.quantita} porzioni", inline=True)
                embed.add_field(name="📅 Per il giorno", value=GIORNI[self.giorno], inline=True)
                embed.add_field(name="📢 Reminder", value=f"{GIORNI[reminder_day]} alle {orario}", inline=True)
                embed.add_field(name="🛒 Da comprare", value=f"{self.portion_to_buy}g", inline=True)
                
                await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            print(f"❌ Errore nel callback orario: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    content="❌ Si è verificato un errore. Riprova!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    content="❌ Si è verificato un errore. Riprova!",
                    ephemeral=True
                )


class ConfermaIncrementoView(ui.View):
    """View per confermare l'incremento di un alimento esistente"""
    def __init__(self, alimento_esistente, alimento_nuovo, user_id):
        super().__init__(timeout=180)
        self.alimento_esistente = alimento_esistente
        self.alimento_nuovo = alimento_nuovo
        self.user_id = user_id
    
    @ui.button(label="✅ Sì, aggiungi quantità", style=discord.ButtonStyle.green)
    async def conferma_button(self, interaction: discord.Interaction, button: ui.Button):
        try:
            await interaction.response.defer()
            
            # Incrementa la quantità
            result = DatabaseManager.incrementa_quantita_alimento(
                self.alimento_esistente['id_univoco'],
                self.alimento_nuovo['quantita']
            )
            
            if result:
                nuova_quantita = self.alimento_esistente['quantita'] + self.alimento_nuovo['quantita']
                
                embed = discord.Embed(
                    title="✅ Quantità Aggiornata!",
                    description=f"**{self.alimento_esistente['nome_alimento'].capitalize()}** aggiornato!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📦 Nuova Quantità",
                    value=f"{nuova_quantita} porzioni",
                    inline=True
                )
                embed.add_field(
                    name="📅 Per il giorno",
                    value=GIORNI[self.alimento_esistente['scongela_per_giorno']],
                    inline=True
                )
                
                await interaction.edit_original_response(embed=embed, view=None)
            else:
                await interaction.followup.send(
                    content="❌ Errore durante l'aggiornamento. Riprova!",
                    ephemeral=True
                )
        except Exception as e:
            print(f"❌ Errore conferma incremento: {e}")
            await interaction.followup.send(
                content="❌ Si è verificato un errore. Riprova!",
                ephemeral=True
            )
    
    @ui.button(label="❌ No, annulla", style=discord.ButtonStyle.red)
    async def annulla_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.edit_original_response(
            content="❌ Operazione annullata.",
            view=None
        )



class ModificaAlimentiView(ui.View):
    """View per la modifica degli alimenti"""
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        
        alimenti = DatabaseManager.get_alimenti_utente(user_id)
        
        if alimenti:
            options = []
            for alimento in alimenti[:25]:
                label = f"{alimento['nome_alimento'].capitalize()} - {GIORNI[alimento['scongela_per_giorno']]}"
                options.append(discord.SelectOption(
                    label=label,
                    value=alimento['id_univoco']
                ))
            
            select = ui.Select(
                placeholder="Seleziona alimento da modificare",
                options=options
            )
            select.callback = self.select_callback
            self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        id_univoco = interaction.data['values'][0]
        alimento = DatabaseManager.get_alimento_by_id(self.user_id, id_univoco)
        await UIHandlers.mostra_menu_modifica(interaction, alimento)
    
    @ui.button(label="◀️ Menu", style=discord.ButtonStyle.secondary, row=1)
    async def menu(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_menu_principale(interaction)


class ModificaAlimentoView(ui.View):
    """View per modificare singolo alimento"""
    def __init__(self, alimento, user_id):
        super().__init__(timeout=180)
        self.alimento = alimento
        self.user_id = user_id
        self.id_univoco = alimento['id_univoco']
    
    @ui.button(label="📅 Cambia Giorno", style=discord.ButtonStyle.primary)
    async def cambia_giorno(self, interaction: discord.Interaction, button: ui.Button):
        print("🔴 BOTTONE CAMBIA GIORNO PREMUTO")
        
        options = [discord.SelectOption(label=giorno, value=str(num)) 
                for num, giorno in GIORNI.items()]
        
        select = ui.Select(placeholder="Nuovo giorno", options=options)
        
        async def callback(inter):
            print("🔵 CALLBACK SELECT AVVIATA")
            await inter.response.defer()
            
            try:
                nuovo_giorno = int(inter.data['values'][0])
                print(f"📝 Nuovo giorno: {nuovo_giorno}")
                
                reminder_day = AlimentoHelper.calcola_reminder_day(nuovo_giorno)
                
                # Calcola nuovo id_univoco
                nuovo_id_univoco = AlimentoHelper.crea_id_univoco(
                    self.alimento['nome_alimento'],
                    nuovo_giorno,
                    self.alimento['portion_to_buy'],
                    self.user_id
                )
                
                # Elimina il vecchio alimento
                DatabaseManager.rimuovi_alimento(self.user_id, self.id_univoco)
                print("✅ Vecchio alimento eliminato")
                
                # Prepara il nuovo alimento aggiornato
                alimento_aggiornato = self.alimento.copy()
                alimento_aggiornato['id_univoco'] = nuovo_id_univoco
                alimento_aggiornato['scongela_per_giorno'] = nuovo_giorno
                alimento_aggiornato['reminder_day'] = reminder_day
                
                # Inserisci il nuovo alimento
                DatabaseManager.inserisci_alimento_nuovo(alimento_aggiornato)
                print("✅ Nuovo alimento inserito")
                
                # ⭐ IMPORTANTE: Aggiorna self.alimento con i nuovi dati
                self.alimento = alimento_aggiornato
                self.id_univoco = nuovo_id_univoco
                print(f"✅ self.alimento aggiornato: Giorno {GIORNI[nuovo_giorno]}")
                
                # ⭐ Ricrea l'embed CON i dati aggiornati
                from ui_handlers import UIHandlers
                embed = UIHandlers.crea_embed_alimento(self.alimento)
                
                await inter.edit_original_response(
                    embed=embed,
                    view=self
                )
                print("✅ CALLBACK COMPLETATA")
                
            except Exception as e:
                print(f"❌ ERRORE: {e}")
                import traceback
                traceback.print_exc()

        
        select.callback = callback
        view = ui.View()
        view.add_item(select)
        print("🔄 Mostrando select menu...")
        await interaction.response.edit_message(view=view)
        print("✅ SELECT MENU VISUALIZZATO")

    
    @ui.button(label="🕐 Cambia Orario", style=discord.ButtonStyle.primary)
    async def cambia_orario(self, interaction: discord.Interaction, button: ui.Button):
        orari = [f"{h:02d}:00" for h in range(8, 23)]
        options = [discord.SelectOption(label=orario, value=orario) for orario in orari]
        
        select = ui.Select(placeholder="Nuovo orario", options=options)
        
        async def callback(inter):
            await inter.response.defer()
            nuovo_orario = inter.data['values'][0]
            
            DatabaseManager.aggiorna_alimento(
                self.user_id, self.id_univoco,
                {"reminder_hours": nuovo_orario}
            )
            
            await inter.edit_original_response(
                content=f"✅ Orario aggiornato a **{nuovo_orario}**!",
                view=None
            )
        
        select.callback = callback
        view = ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)
    
    @ui.button(label="🔔 Notifiche", style=discord.ButtonStyle.secondary)
    async def toggle_notifiche(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        stato_attuale = self.alimento['notifiche_abilitate']
        nuovo_stato = not stato_attuale
        
        DatabaseManager.aggiorna_alimento(
            self.user_id, self.id_univoco,
            {"notifiche_abilitate": nuovo_stato}
        )
        
        stato_testo = "attivate ✅" if nuovo_stato else "disattivate ❌"
        await interaction.edit_original_response(
            content=f"Notifiche {stato_testo}!",
            view=None
        )
    
    @ui.button(label="◀️ Indietro", style=discord.ButtonStyle.secondary, row=1)
    async def indietro(self, interaction: discord.Interaction, button: ui.Button):
        from ui_handlers import UIHandlers
        await interaction.response.defer()
        await UIHandlers.mostra_lista(interaction)

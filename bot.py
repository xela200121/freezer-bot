import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio


# Carica variabili d'ambiente
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')


# Connessione MongoDB
client = MongoClient(MONGODB_URI)
db = client['freezerbot']
alimenti_collection = db['alimenti']


# Configurazione bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# Scheduler per notifiche
scheduler = AsyncIOScheduler()


# Dizionari di mapping
GIORNI = {
    1: "Lunedì", 2: "Martedì", 3: "Mercoledì", 
    4: "Giovedì", 5: "Venerdì", 6: "Sabato", 7: "Domenica"
}


GIORNI_INVERSO = {v: k for k, v in GIORNI.items()}


# ==================== FUNZIONI HELPER ====================


def crea_id_univoco(nome, giorno, portion):
    """Crea ID univoco per l'alimento"""
    return f"{nome.lower()}_{giorno}_{portion}"


def get_alimenti_utente(user_id):
    """Ottiene tutti gli alimenti di un utente"""
    return list(alimenti_collection.find({"user_id": str(user_id)}))


def get_alimento_by_id(user_id, id_univoco):
    """Ottiene un alimento specifico"""
    return alimenti_collection.find_one({
        "user_id": str(user_id),
        "id_univoco": id_univoco
    })


def aggiorna_quantita(user_id, id_univoco, delta):
    """Aggiorna la quantità di un alimento"""
    alimento = get_alimento_by_id(user_id, id_univoco)
    if not alimento:
        return None
    
    nuova_quantita = max(0, alimento['quantita'] + delta)
    
    alimenti_collection.update_one(
        {"user_id": str(user_id), "id_univoco": id_univoco},
        {"$set": {"quantita": nuova_quantita}}
    )
    
    return nuova_quantita


def rimuovi_alimento(user_id, id_univoco):
    """Rimuove un alimento"""
    result = alimenti_collection.delete_one({
        "user_id": str(user_id),
        "id_univoco": id_univoco
    })
    return result.deleted_count > 0


# ==================== VIEWS (BOTTONI E MENU) ====================


class MenuPrincipale(discord.ui.View):
    """Menu principale con pulsanti Lista, Aggiungi, Impostazioni"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📋 Lista", style=discord.ButtonStyle.primary, custom_id="lista")
    async def lista_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_lista(interaction)
    
    @discord.ui.button(label="➕ Aggiungi", style=discord.ButtonStyle.green, custom_id="aggiungi")
    async def aggiungi_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_menu_aggiungi(interaction)
    
    @discord.ui.button(label="⚙️ Impostazioni", style=discord.ButtonStyle.secondary, custom_id="impostazioni")
    async def impostazioni_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_impostazioni(interaction)



class ListaAlimentiView(discord.ui.View):
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
            select = discord.ui.Select(
                placeholder="Seleziona un alimento da gestire",
                options=options,
                custom_id="select_alimento"
            )
            select.callback = self.select_callback
            self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        id_univoco = interaction.data['values'][0]
        await interaction.response.defer()
        await mostra_gestione_alimento(interaction, id_univoco)
    
    @discord.ui.button(label="🏠 Menu", style=discord.ButtonStyle.secondary, row=4)
    async def menu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_menu_principale(interaction)



class GestioneAlimentoView(discord.ui.View):
    """View per gestire singolo alimento (+1, -1, Rimuovi)"""
    def __init__(self, alimento, user_id):
        super().__init__(timeout=180)
        self.alimento = alimento
        self.user_id = user_id
        self.id_univoco = alimento['id_univoco']
    
    @discord.ui.button(label="➕ Aggiungi 1", style=discord.ButtonStyle.green)
    async def aggiungi_uno(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        nuova_quantita = aggiorna_quantita(self.user_id, self.id_univoco, 1)
        self.alimento['quantita'] = nuova_quantita
        await interaction.edit_original_response(
            embed=crea_embed_alimento(self.alimento),
            view=self
        )
    
    @discord.ui.button(label="➖ Rimuovi 1", style=discord.ButtonStyle.red)
    async def rimuovi_uno(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        nuova_quantita = aggiorna_quantita(self.user_id, self.id_univoco, -1)
        self.alimento['quantita'] = nuova_quantita
        
        # Notifica se finito
        if nuova_quantita == 1:
            await notifica_quantita_finita(interaction.user, self.alimento)
        
        await interaction.edit_original_response(
            embed=crea_embed_alimento(self.alimento),
            view=self
        )
    
    @discord.ui.button(label="🗑️ Elimina", style=discord.ButtonStyle.danger)
    async def elimina(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        rimuovi_alimento(self.user_id, self.id_univoco)
        await interaction.edit_original_response(
            content=f"✅ **{self.alimento['nome_alimento']}** eliminato dal freezer!",
            embed=None,
            view=None
        )
    
    @discord.ui.button(label="⚙️ Modifica", style=discord.ButtonStyle.secondary)
    async def modifica(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_menu_modifica(interaction, self.alimento)
    
    @discord.ui.button(label="◀️ Indietro", style=discord.ButtonStyle.secondary, row=2)
    async def indietro(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_lista(interaction)



class AggiungiAlimentoView(discord.ui.View):
    """View per aggiungere nuovo alimento o porzione esistente"""
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        
        # Ottieni alimenti esistenti
        alimenti = get_alimenti_utente(user_id)
        
        if alimenti:
            # Crea set di nomi unici
            nomi_unici = list(set([a['nome_alimento'] for a in alimenti]))
            
            if nomi_unici:
                options = [discord.SelectOption(label=nome.capitalize(), value=nome) 
                          for nome in nomi_unici[:25]]
                
                select = discord.ui.Select(
                    placeholder="Aggiungi porzione a alimento esistente",
                    options=options
                )
                select.callback = self.select_esistente_callback
                self.add_item(select)
    
    async def select_esistente_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        nome = interaction.data['values'][0]
        # Mostra gli alimenti con quel nome per scegliere quale incrementare
        alimenti = [a for a in get_alimenti_utente(self.user_id) if a['nome_alimento'] == nome]
        
        if len(alimenti) == 1:
            # Solo uno, incrementa direttamente
            aggiorna_quantita(self.user_id, alimenti[0]['id_univoco'], 1)
            await interaction.edit_original_response(
                content=f"✅ Aggiunta 1 porzione di **{nome}**!",
                view=None
            )
        else:
            # Più di uno, chiedi quale
            await mostra_selezione_variante(interaction, nome, alimenti)
    
    @discord.ui.button(label="➕ Nuovo Alimento", style=discord.ButtonStyle.green, row=1)
    async def nuovo_alimento(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NuovoAlimentoModal())
    
    @discord.ui.button(label="◀️ Indietro", style=discord.ButtonStyle.secondary, row=1)
    async def indietro(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_menu_principale(interaction)



class NuovoAlimentoModal(discord.ui.Modal, title="➕ Aggiungi Nuovo Alimento"):
    """Modal per inserire dati nuovo alimento"""
    
    nome = discord.ui.TextInput(
        label="Nome Alimento",
        placeholder="es: Pollo, Pesce, Verdure...",
        required=True,
        max_length=50
    )
    
    quantita = discord.ui.TextInput(
        label="Quantità",
        placeholder="es: 3",
        required=True,
        max_length=5,
        default="1"
    )
    
    portion_to_buy = discord.ui.TextInput(
        label="Grammi/Porzione da comprare",
        placeholder="es: 150",
        required=True,
        max_length=5,
        default="150"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Mostra menu per scegliere giorno
        await mostra_selezione_giorno(
            interaction,
            self.nome.value,
            int(self.quantita.value),
            int(self.portion_to_buy.value)
        )



class SelezioneGiornoView(discord.ui.View):
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
        
        select = discord.ui.Select(
            placeholder="Per quale giorno lo scongeli?",
            options=options
        )
        select.callback = self.select_giorno_callback
        self.add_item(select)
    
    async def select_giorno_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        giorno = int(interaction.data['values'][0])
        await mostra_selezione_orario(
            interaction,
            self.nome,
            self.quantita,
            self.portion_to_buy,
            giorno
        )



class SelezioneOrarioView(discord.ui.View):
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
        
        select = discord.ui.Select(
            placeholder="A che ora vuoi il promemoria?",
            options=options
        )
        select.callback = self.select_orario_callback
        self.add_item(select)
    
    async def select_orario_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        orario = interaction.data['values'][0]
        
        # Calcola giorno reminder (giorno prima)
        reminder_day = self.giorno - 1 if self.giorno > 1 else 7
        
        # Crea ID univoco
        id_univoco = crea_id_univoco(self.nome, self.giorno, self.portion_to_buy)
        
        # Salva nel database
        alimenti_collection.insert_one({
            "user_id": str(self.user_id),
            "id_univoco": id_univoco,
            "nome_alimento": self.nome.lower(),
            "quantita": self.quantita,
            "unita": "porzioni",
            "reminder_day": reminder_day,
            "reminder_hours": orario,
            "notifiche_abilitate": True,
            "scongela_per_giorno": self.giorno,
            "portion_to_buy": self.portion_to_buy,
            "ultima_notifica": None
        })
        
        embed = discord.Embed(
            title="✅ Alimento Aggiunto!",
            description=f"**{self.nome.capitalize()}** è stato aggiunto al freezer!",
            color=discord.Color.green()
        )
        embed.add_field(name="📦 Quantità", value=f"{self.quantita} porzioni", inline=True)
        embed.add_field(name="📅 Per il giorno", value=GIORNI[self.giorno], inline=True)
        embed.add_field(name="🔔 Reminder", value=f"{GIORNI[reminder_day]} alle {orario}", inline=True)
        embed.add_field(name="🛒 Da comprare", value=f"{self.portion_to_buy}g", inline=True)
        
        await interaction.edit_original_response(embed=embed, view=None)



class ImpostazioniView(discord.ui.View):
    """View per le impostazioni"""
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        
        alimenti = get_alimenti_utente(user_id)
        
        if alimenti:
            options = []
            for alimento in alimenti[:25]:
                label = f"{alimento['nome_alimento'].capitalize()} - {GIORNI[alimento['scongela_per_giorno']]}"
                options.append(discord.SelectOption(
                    label=label,
                    value=alimento['id_univoco']
                ))
            
            select = discord.ui.Select(
                placeholder="Seleziona alimento da modificare",
                options=options
            )
            select.callback = self.select_callback
            self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        id_univoco = interaction.data['values'][0]
        alimento = get_alimento_by_id(self.user_id, id_univoco)
        await mostra_menu_modifica(interaction, alimento)
    
    @discord.ui.button(label="◀️ Menu", style=discord.ButtonStyle.secondary, row=1)
    async def menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_menu_principale(interaction)



class ModificaAlimentoView(discord.ui.View):
    """View per modificare singolo alimento"""
    def __init__(self, alimento, user_id):
        super().__init__(timeout=180)
        self.alimento = alimento
        self.user_id = user_id
        self.id_univoco = alimento['id_univoco']
    
    @discord.ui.button(label="📅 Cambia Giorno", style=discord.ButtonStyle.primary)
    async def cambia_giorno(self, interaction: discord.Interaction, button: discord.ui.Button):
        options = [discord.SelectOption(label=giorno, value=str(num)) 
                  for num, giorno in GIORNI.items()]
        
        select = discord.ui.Select(placeholder="Nuovo giorno", options=options)
        
        async def callback(inter):
            await inter.response.defer()
            nuovo_giorno = int(inter.data['values'][0])
            reminder_day = nuovo_giorno - 1 if nuovo_giorno > 1 else 7
            
            alimenti_collection.update_one(
                {"user_id": str(self.user_id), "id_univoco": self.id_univoco},
                {"$set": {
                    "scongela_per_giorno": nuovo_giorno,
                    "reminder_day": reminder_day
                }}
            )
            
            await inter.edit_original_response(
                content=f"✅ Giorno aggiornato a **{GIORNI[nuovo_giorno]}**!",
                view=None
            )
        
        select.callback = callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)
    
    @discord.ui.button(label="🕐 Cambia Orario", style=discord.ButtonStyle.primary)
    async def cambia_orario(self, interaction: discord.Interaction, button: discord.ui.Button):
        orari = [f"{h:02d}:00" for h in range(8, 23)]
        options = [discord.SelectOption(label=orario, value=orario) for orario in orari]
        
        select = discord.ui.Select(placeholder="Nuovo orario", options=options)
        
        async def callback(inter):
            await inter.response.defer()
            nuovo_orario = inter.data['values'][0]
            
            alimenti_collection.update_one(
                {"user_id": str(self.user_id), "id_univoco": self.id_univoco},
                {"$set": {"reminder_hours": nuovo_orario}}
            )
            
            await inter.edit_original_response(
                content=f"✅ Orario aggiornato a **{nuovo_orario}**!",
                view=None
            )
        
        select.callback = callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)
    
    @discord.ui.button(label="🔔 Notifiche", style=discord.ButtonStyle.secondary)
    async def toggle_notifiche(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        stato_attuale = self.alimento['notifiche_abilitate']
        nuovo_stato = not stato_attuale
        
        alimenti_collection.update_one(
            {"user_id": str(self.user_id), "id_univoco": self.id_univoco},
            {"$set": {"notifiche_abilitate": nuovo_stato}}
        )
        
        stato_testo = "attivate ✅" if nuovo_stato else "disattivate ❌"
        await interaction.edit_original_response(
            content=f"Notifiche {stato_testo}!",
            view=None
        )
    
    @discord.ui.button(label="◀️ Indietro", style=discord.ButtonStyle.secondary, row=1)
    async def indietro(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await mostra_lista(interaction)



# ==================== FUNZIONI DI VISUALIZZAZIONE ====================


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
        name="⚙️ Impostazioni",
        value="Modifica reminder e notifiche",
        inline=False
    )
    
    view = MenuPrincipale()
    
    await interaction.edit_original_response(embed=embed, view=view)



async def mostra_lista(interaction: discord.Interaction):
    """Mostra la lista degli alimenti"""
    if not interaction.response.is_done():
        await interaction.response.defer()
    
    alimenti = get_alimenti_utente(interaction.user.id)
    
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



async def mostra_gestione_alimento(interaction: discord.Interaction, id_univoco: str):
    """Mostra la gestione di un singolo alimento"""
    alimento = get_alimento_by_id(interaction.user.id, id_univoco)
    
    if not alimento:
        await interaction.edit_original_response(content="❌ Alimento non trovato!")
        return
    
    embed = crea_embed_alimento(alimento)
    view = GestioneAlimentoView(alimento, interaction.user.id)
    
    await interaction.edit_original_response(embed=embed, view=view)



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
        name="🔔 Reminder",
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
        aggiorna_quantita(interaction.user.id, id_univoco, 1)
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



async def mostra_selezione_giorno(interaction: discord.Interaction, nome: str, quantita: int, portion_to_buy: int):
    """Mostra menu per selezionare il giorno"""
    embed = discord.Embed(
        title="📅 Seleziona Giorno",
        description=f"Per quale giorno vuoi scongelare **{nome.capitalize()}**?",
        color=discord.Color.blue()
    )
    
    view = SelezioneGiornoView(nome, quantita, portion_to_buy, interaction.user.id)
    await interaction.edit_original_response(embed=embed, view=view)



async def mostra_selezione_orario(interaction: discord.Interaction, nome: str, quantita: int, portion_to_buy: int, giorno: int):
    """Mostra menu per selezionare l'orario"""
    embed = discord.Embed(
        title="🕐 Seleziona Orario",
        description=f"A che ora vuoi ricevere il promemoria per **{nome.capitalize()}**?\n(Il giorno prima: {GIORNI[giorno-1 if giorno > 1 else 7]})",
        color=discord.Color.blue()
    )
    
    view = SelezioneOrarioView(nome, quantita, portion_to_buy, giorno, interaction.user.id)
    await interaction.edit_original_response(embed=embed, view=view)



async def mostra_impostazioni(interaction: discord.Interaction):
    """Mostra menu impostazioni"""
    if not interaction.response.is_done():
        await interaction.response.defer()
    
    alimenti = get_alimenti_utente(interaction.user.id)
    
    if not alimenti:
        embed = discord.Embed(
            title="⚙️ Impostazioni",
            description="Non hai ancora alimenti da configurare!",
            color=discord.Color.orange()
        )
        view = MenuPrincipale()
    else:
        embed = discord.Embed(
            title="⚙️ Impostazioni",
            description="Seleziona un alimento da modificare:",
            color=discord.Color.blue()
        )
        view = ImpostazioniView(interaction.user.id)
    
    await interaction.edit_original_response(embed=embed, view=view)



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



# ==================== SISTEMA NOTIFICHE ====================


async def notifica_quantita_finita(user, alimento):
    """Invia notifica quando la quantità finisce"""
    try:
        embed = discord.Embed(
            title="⚠️ Alimento Terminato!",
            description=f"Hai finito **{alimento['nome_alimento'].capitalize()}**!",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="🛒 Da comprare",
            value=f"{alimento['portion_to_buy']}g per {GIORNI[alimento['scongela_per_giorno']]}",
            inline=False
        )
        
        await user.send(embed=embed)
    except discord.Forbidden:
        print(f"Impossibile inviare DM a {user.id}")



async def controlla_reminder():
    """Controlla e invia reminder programmati"""
    ora_attuale = datetime.now()
    giorno_attuale = ora_attuale.weekday() + 1  # 1=lunedì
    ora_formattata = ora_attuale.strftime("%H:00")
    
    # Cerca tutti gli alimenti con reminder per oggi a quest'ora
    alimenti = alimenti_collection.find({
        "notifiche_abilitate": True,
        "reminder_day": giorno_attuale,
        "reminder_hours": ora_formattata,
        "quantita": {"$gt": 0}  # Solo se c'è quantità disponibile
    })
    
    for alimento in alimenti:
        # Controlla se già notificato oggi
        ultima_notifica = alimento.get('ultima_notifica')
        
        if ultima_notifica:
            ultima_data = datetime.fromisoformat(ultima_notifica)
            if ultima_data.date() == ora_attuale.date():
                continue  # Già notificato oggi
        
        try:
            user = await bot.fetch_user(int(alimento['user_id']))
            
            embed = discord.Embed(
                title="🔔 Promemoria Scongelamento!",
                description=f"Ricorda di tirare fuori **{alimento['nome_alimento'].capitalize()}**!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📅 Per domani",
                value=GIORNI[alimento['scongela_per_giorno']],
                inline=True
            )
            embed.add_field(
                name="📦 Disponibili",
                value=f"{alimento['quantita']} {alimento.get('unita', 'pz')}",
                inline=True
            )
            
            await user.send(embed=embed)
            
            # Aggiorna ultima notifica
            alimenti_collection.update_one(
                {"_id": alimento['_id']},
                {"$set": {"ultima_notifica": ora_attuale.isoformat()}}
            )
            
        except discord.Forbidden:
            print(f"Impossibile inviare DM a {alimento['user_id']}")
        except Exception as e:
            print(f"Errore invio notifica: {e}")



# ==================== COMANDI SLASH ====================


@bot.tree.command(name="menu", description="Mostra il menu principale di FreezerBot")
async def menu_command(interaction: discord.Interaction):
    """Comando /menu per aprire il menu principale"""
    await mostra_menu_principale(interaction)



@bot.tree.command(name="lista", description="Mostra tutti gli alimenti nel freezer")
async def lista_command(interaction: discord.Interaction):
    """Comando /lista per vedere gli alimenti"""
    await mostra_lista(interaction)



@bot.tree.command(name="aggiungi", description="Aggiungi alimenti o porzioni")
async def aggiungi_command(interaction: discord.Interaction):
    """Comando /aggiungi"""
    await mostra_menu_aggiungi(interaction)



@bot.tree.command(name="impostazioni", description="Modifica impostazioni alimenti")
async def impostazioni_command(interaction: discord.Interaction):
    """Comando /impostazioni"""
    await mostra_impostazioni(interaction)



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
              "`/aggiungi` - Aggiungi alimenti\n"
              "`/impostazioni` - Modifica configurazioni",
        inline=False
    )
    
    embed.add_field(
        name="🔔 Come funzionano i promemoria?",
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



# ==================== EVENTI BOT ====================


@bot.event
async def on_ready():
    """Evento quando il bot si connette"""
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
        scheduler.add_job(controlla_reminder, 'interval', minutes=60)
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
async def on_command_error(ctx, error):
    """Gestisce errori nei comandi"""
    if isinstance(error, commands.CommandNotFound):
        return
    print(f'Errore: {error}')


from aiohttp import web
import threading

# ==================== SERVER HTTP PER RENDER FITTIZIO ====================

async def health_check(request):
    """Endpoint per health check di Render"""
    return web.Response(text="Bot is running!")

async def start_web_server():
    """Avvia un semplice web server per Render"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    port = int(os.getenv('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'✅ Web server avviato sulla porta {port}')


# ==================== AVVIO BOT ====================


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(start_web_server())  # Avvia il web server in parallelo
        loop.create_task(bot.start(TOKEN))    # Avvia il bot
        loop.run_forever()
    except KeyboardInterrupt:
        print("🛑 Arresto manuale del bot...")
    finally:
        loop.run_until_complete(bot.close())
        print("✅ Bot chiuso correttamente.")

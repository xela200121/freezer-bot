# config.py
"""Configurazione e costanti del bot"""

import os
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Credenziali
TOKEN = os.getenv('DISCORD_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')

# Configurazione web server
PORT = int(os.getenv('PORT', 10000))

# Dizionari di mapping
GIORNI = {
    1: "Lunedì", 2: "Martedì", 3: "Mercoledì", 
    4: "Giovedì", 5: "Venerdì", 6: "Sabato", 7: "Domenica"
}

GIORNI_INVERSO = {v: k for k, v in GIORNI.items()}

# Nomi canali
NOME_CANALE_LISTA_SPESA = "lista-spesa"

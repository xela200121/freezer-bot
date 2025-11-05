# database.py
"""Gestione connessione MongoDB e operazioni database"""

from pymongo import MongoClient
from datetime import datetime
from config import MONGODB_URI

# Connessione MongoDB
client = MongoClient(MONGODB_URI)
db = client['freezerbot']
alimenti_collection = db['alimenti']
user_threads_collection = db['user_threads']


class DatabaseManager:
    """Manager per le operazioni sul database"""
    
    @staticmethod
    def get_alimenti_utente(user_id):
        """Ottiene tutti gli alimenti di un utente"""
        return list(alimenti_collection.find({"user_id": str(user_id)}))
    
    @staticmethod
    def get_alimento_by_id(user_id, id_univoco):
        """Ottiene un alimento specifico"""
        return alimenti_collection.find_one({
            "user_id": str(user_id),
            "id_univoco": id_univoco
        })
    
    @staticmethod
    def aggiorna_quantita(user_id, id_univoco, delta):
        """Aggiorna la quantità di un alimento"""
        alimento = DatabaseManager.get_alimento_by_id(user_id, id_univoco)
        if not alimento:
            return None
        
        nuova_quantita = max(0, alimento['quantita'] + delta)
        
        alimenti_collection.update_one(
            {"user_id": str(user_id), "id_univoco": id_univoco},
            {"$set": {"quantita": nuova_quantita}}
        )
        
        return nuova_quantita
    
    @staticmethod
    def rimuovi_alimento(user_id, id_univoco):
        """Rimuove un alimento"""
        result = alimenti_collection.delete_one({
            "user_id": str(user_id),
            "id_univoco": id_univoco
        })
        return result.deleted_count > 0
    
    @staticmethod
    def inserisci_alimento(alimento_data):
        """Inserisce un nuovo alimento o aggiorna la quantità se esiste"""
        result = alimenti_collection.update_one(
            {"id_univoco": alimento_data["id_univoco"]},
            {
                "$inc": {"quantita": alimento_data["quantita"]},
                "$setOnInsert": alimento_data
            },
            upsert=True
        )
        return result


    
    @staticmethod
    def aggiorna_alimento(user_id, id_univoco, updates):
        """Aggiorna i campi di un alimento"""
        return alimenti_collection.update_one(
            {"user_id": str(user_id), "id_univoco": id_univoco},
            {"$set": updates}
        )
    
    @staticmethod
    def get_user_thread(guild_id, user_id):
        """Ottiene il thread di un utente"""
        return user_threads_collection.find_one({
            "guild_id": str(guild_id),
            "user_id": str(user_id)
        })
    
    @staticmethod
    def save_user_thread(guild_id, user_id, channel_id, thread_id):
        """Salva il thread di un utente"""
        user_threads_collection.update_one(
            {"guild_id": str(guild_id), "user_id": str(user_id)},
            {"$set": {
                "channel_id": str(channel_id),
                "thread_id": str(thread_id),
                "created_at": datetime.now().isoformat()
            }},
            upsert=True
        )
    
    @staticmethod
    def get_alimenti_per_reminder(giorno_attuale, ora_formattata):
        """Ottiene gli alimenti che necessitano di reminder"""
        return alimenti_collection.find({
            "notifiche_abilitate": True,
            "reminder_day": giorno_attuale,
            "reminder_hours": ora_formattata,
            "quantita": {"$gt": 0}
        })
    
    @staticmethod
    def aggiorna_ultima_notifica(alimento_id, timestamp):
        """Aggiorna il timestamp dell'ultima notifica"""
        alimenti_collection.update_one(
            {"_id": alimento_id},
            {"$set": {"ultima_notifica": timestamp}}
        )

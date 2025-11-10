# database.py
"""Gestione connessione MongoDB e operazioni database"""

from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from config import MONGODB_URI

# Connessione MongoDB
client = MongoClient(MONGODB_URI)
db = client['freezerbot']
alimenti_collection = db['alimenti']
user_threads_collection = db['user_threads']
notification_queue_collection = db['notification_queue'] 


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
    def get_alimento_by_object_id(alimento_id):
        """Ottiene un alimento tramite ObjectId"""
        try:
            return alimenti_collection.find_one({"_id": ObjectId(alimento_id)})
        except Exception as e:
            print(f"❌ Errore get_alimento_by_object_id: {e}")
            return None
    
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
    def alimento_esiste(id_univoco):
        """Controlla se un alimento esiste già"""
        try:
            alimento = alimenti_collection.find_one({"id_univoco": id_univoco})
            return alimento
        except Exception as e:
            print(f"❌ Errore controllo esistenza: {e}")
            return None

    @staticmethod
    def inserisci_alimento_nuovo(alimento_data):
        """Inserisce un nuovo alimento SENZA fare upsert"""
        try:
            result = alimenti_collection.insert_one(alimento_data)
            print(f"✅ Alimento inserito: {alimento_data['nome_alimento']}")
            return result
        except Exception as e:
            print(f"❌ Errore inserimento: {e}")
            return None

    @staticmethod
    def incrementa_quantita_alimento(id_univoco, quantita_da_aggiungere):
        """Incrementa la quantità di un alimento esistente"""
        try:
            result = alimenti_collection.update_one(
                {"id_univoco": id_univoco},
                {"$inc": {"quantita": quantita_da_aggiungere}}
            )
            print(f"✅ Quantità incrementata per {id_univoco}")
            return result
        except Exception as e:
            print(f"❌ Errore incremento: {e}")
            return None
    
    @staticmethod
    def aggiorna_alimento(user_id, id_univoco, updates):
        """Aggiorna i campi di un alimento"""
        return alimenti_collection.update_one(
            {"user_id": str(user_id), "id_univoco": id_univoco},
            {"$set": updates}
        )
    
    @staticmethod
    def aggiorna_ultima_notifica(alimento_id, timestamp):
        """Aggiorna il timestamp dell'ultima notifica"""
        try:
            alimenti_collection.update_one(
                {"_id": ObjectId(alimento_id)},
                {"$set": {"ultima_notifica": timestamp}}
            )
        except Exception as e:
            print(f"❌ Errore aggiornamento ultima_notifica: {e}")
    
    @staticmethod
    def get_alimenti_per_reminder(giorno_attuale, ora_formattata):
        """Ottiene gli alimenti che necessitano di reminder (metodo legacy)"""
        return alimenti_collection.find({
            "notifiche_abilitate": True,
            "reminder_day": giorno_attuale,
            "reminder_hours": ora_formattata,
            "quantita": {"$gt": 0}
        })
    
    @staticmethod
    def get_alimenti_per_giorno(giorno):
        """Ottiene tutti gli alimenti con reminder per un giorno specifico"""
        return alimenti_collection.find({
            "notifiche_abilitate": True,
            "reminder_day": giorno,
            "quantita": {"$gt": 0}
        })
    
    
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
    def crea_notifica_in_coda(alimento_id, user_id, alimento_nome, data_notifica, 
                               orario_notifica, datetime_notifica):
        """Crea una nuova notifica nella coda"""
        try:
            notification_queue_collection.insert_one({
                "alimento_id": str(alimento_id),
                "user_id": str(user_id),
                "alimento_nome": alimento_nome,
                "data_notifica": data_notifica,
                "orario_notifica": orario_notifica,
                "datetime_notifica": datetime_notifica,
                "stato": "pending",  # pending, sent, failed, skipped
                "tentativi": 0,
                "max_tentativi": 3,
                "created_at": datetime.now().isoformat(),
                "sent_at": None,
                "errore": None
            })
            return True
        except Exception as e:
            print(f"❌ Errore creazione notifica in coda: {e}")
            return False
    
    @staticmethod
    def notifica_in_coda_esiste(alimento_id, data_notifica):
        """Controlla se esiste già una notifica in coda per quell'alimento in quella data"""
        return notification_queue_collection.find_one({
            "alimento_id": str(alimento_id),
            "data_notifica": data_notifica,
            "stato": {"$in": ["pending", "sent"]}
        })
    
    @staticmethod
    def get_notifiche_da_inviare(ora_attuale_iso):
        """Ottiene le notifiche pending il cui orario è passato"""
        return notification_queue_collection.find({
            "stato": "pending",
            "datetime_notifica": {"$lte": ora_attuale_iso},
            "tentativi": {"$lt": 3}
        })
    
    @staticmethod
    def marca_notifica_come_inviata(notifica_id, tentativi):
        """Marca una notifica come inviata con successo"""
        try:
            notification_queue_collection.update_one(
                {"_id": notifica_id},
                {"$set": {
                    "stato": "sent",
                    "sent_at": datetime.now().isoformat(),
                    "tentativi": tentativi + 1
                }}
            )
            return True
        except Exception as e:
            print(f"❌ Errore marca_notifica_come_inviata: {e}")
            return False
    
    @staticmethod
    def marca_notifica_come_fallita(notifica_id, errore):
        """Marca una notifica come fallita"""
        try:
            notification_queue_collection.update_one(
                {"_id": notifica_id},
                {"$set": {
                    "stato": "failed",
                    "errore": errore
                }}
            )
            return True
        except Exception as e:
            print(f"❌ Errore marca_notifica_come_fallita: {e}")
            return False
    
    @staticmethod
    def marca_notifica_come_skipped(notifica_id, errore):
        """Marca una notifica come saltata (es: quantità 0)"""
        try:
            notification_queue_collection.update_one(
                {"_id": notifica_id},
                {"$set": {
                    "stato": "skipped",
                    "errore": errore
                }}
            )
            return True
        except Exception as e:
            print(f"❌ Errore marca_notifica_come_skipped: {e}")
            return False
    
    @staticmethod
    def incrementa_tentativi_notifica(notifica_id, errore):
        """Incrementa i tentativi di una notifica fallita"""
        try:
            notification_queue_collection.update_one(
                {"_id": notifica_id},
                {
                    "$set": {"errore": errore},
                    "$inc": {"tentativi": 1}
                }
            )
            return True
        except Exception as e:
            print(f"❌ Errore incrementa_tentativi_notifica: {e}")
            return False
    
    @staticmethod
    def marca_notifiche_failed_per_max_tentativi():
        """Marca come failed le notifiche che hanno superato il max tentativi"""
        try:
            result = notification_queue_collection.update_many(
                {"stato": "pending", "tentativi": {"$gte": 3}},
                {"$set": {"stato": "failed"}}
            )
            return result.modified_count
        except Exception as e:
            print(f"❌ Errore marca_notifiche_failed: {e}")
            return 0
    
    @staticmethod
    def elimina_notifiche_vecchie(giorni=7):
        """Elimina notifiche più vecchie di X giorni"""
        from datetime import timedelta
        try:
            data_limite = (datetime.now() - timedelta(days=giorni)).date().isoformat()
            result = notification_queue_collection.delete_many({
                "data_notifica": {"$lt": data_limite}
            })
            return result.deleted_count
        except Exception as e:
            print(f"❌ Errore elimina_notifiche_vecchie: {e}")
            return 0
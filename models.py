# models.py
"""Modelli dati e funzioni helper"""

from config import GIORNI


class AlimentoHelper:
    """Helper per gestire gli alimenti"""
    
    @staticmethod
    def crea_id_univoco(nome, giorno, portion, user_id):
        """Crea ID univoco per l'alimento"""
        return f"{nome.lower()}_{giorno}_{portion}_{user_id}"
    
    @staticmethod
    def calcola_reminder_day(giorno_consumo):
        """Calcola il giorno del reminder (giorno prima)"""
        return giorno_consumo - 1 if giorno_consumo > 1 else 7
    
    @staticmethod
    def crea_alimento_dict(user_id, nome, quantita, portion_to_buy, giorno, orario):
        """Crea dizionario per nuovo alimento"""
        reminder_day = AlimentoHelper.calcola_reminder_day(giorno)
        id_univoco = AlimentoHelper.crea_id_univoco(nome, giorno, portion_to_buy, user_id)
        
        return {
            "user_id": str(user_id),
            "id_univoco": id_univoco,
            "nome_alimento": nome.lower(),
            "quantita": quantita,
            "unita": "porzioni",
            "reminder_day": reminder_day,
            "reminder_hours": orario,
            "notifiche_abilitate": True,
            "scongela_per_giorno": giorno,
            "portion_to_buy": portion_to_buy,
            "ultima_notifica": None
        }
    
    @staticmethod
    def formatta_nome_giorno(giorno_num):
        """Restituisce il nome del giorno dal numero"""
        return GIORNI.get(giorno_num, "Sconosciuto")

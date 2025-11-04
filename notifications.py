# notifications.py
"""Sistema di notifiche e reminder"""

import discord
from datetime import datetime
from database import DatabaseManager
from config import GIORNI


class NotificationManager:
    """Manager per gestire le notifiche"""
    
    @staticmethod
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
    
    @staticmethod
    async def controlla_reminder(bot):
        """Controlla e invia reminder programmati"""
        ora_attuale = datetime.now()
        giorno_attuale = ora_attuale.weekday() + 1  # 1=lunedì
        ora_formattata = ora_attuale.strftime("%H:00")
        
        # Cerca tutti gli alimenti con reminder per oggi a quest'ora
        alimenti = DatabaseManager.get_alimenti_per_reminder(giorno_attuale, ora_formattata)
        
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
                    title="📢 Promemoria Scongelamento!",
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
                DatabaseManager.aggiorna_ultima_notifica(
                    alimento['_id'], 
                    ora_attuale.isoformat()
                )
                
            except discord.Forbidden:
                print(f"Impossibile inviare DM a {alimento['user_id']}")
            except Exception as e:
                print(f"Errore invio notifica: {e}")

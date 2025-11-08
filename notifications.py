# notifications.py
"""Sistema di notifiche e reminder"""

import discord
from datetime import datetime
from database import DatabaseManager
from config import GIORNI


class ConfermaScongelamentoView(discord.ui.View):
    """View per confermare lo scongelamento dalla notifica"""
    def __init__(self, alimento_id, user_id):
        super().__init__(timeout=None)  # Nessun timeout per le notifiche
        self.alimento_id = alimento_id
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Ho Scongelato", style=discord.ButtonStyle.green, custom_id="conferma_scongelato")
    async def conferma_scongelato(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bottone per confermare lo scongelamento e diminuire la quantità"""
        try:
            await interaction.response.defer()
            
            # Recupera l'alimento
            alimento = DatabaseManager.get_alimento_by_id(self.user_id, self.alimento_id)
            
            if not alimento:
                await interaction.followup.send(
                    "❌ Alimento non trovato! Potrebbe essere stato eliminato.",
                    ephemeral=True
                )
                return
            
            # Diminuisci la quantità di 1
            nuova_quantita = DatabaseManager.aggiorna_quantita(
                self.user_id, 
                self.alimento_id, 
                -1
            )
            
            if nuova_quantita is None:
                await interaction.followup.send(
                    "❌ Errore durante l'aggiornamento della quantità.",
                    ephemeral=True
                )
                return
            
            # Crea embed di conferma
            embed = discord.Embed(
                title="✅ Scongelamento Confermato!",
                description=f"**{alimento['nome_alimento'].capitalize()}** scongelato correttamente.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📦 Quantità Rimanente",
                value=f"{nuova_quantita} {alimento.get('unita', 'pz')}",
                inline=True
            )
            
            # Se la quantità è arrivata a 1, avvisa
            if nuova_quantita == 1:
                embed.add_field(
                    name="⚠️ Attenzione",
                    value="È rimasta solo 1 porzione!\n🛒 Ricordati di comprarne altre.",
                    inline=False
                )
                embed.color = discord.Color.orange()
            
            # Se la quantità è 0, avvisa che è finito
            if nuova_quantita == 0:
                embed.add_field(
                    name="🔴 Alimento Terminato",
                    value=f"Non ci sono più porzioni disponibili!\n🛒 Da comprare: {alimento['portion_to_buy']}g",
                    inline=False
                )
                embed.color = discord.Color.red()
            
            # Disabilita il bottone dopo il click
            button.disabled = True
            button.label = "✅ Confermato"
            
            await interaction.edit_original_response(
                embed=embed,
                view=self
            )
            
            # Se la quantità è arrivata a 1, invia anche la notifica di quantità finita
            if nuova_quantita == 1:
                user = await interaction.client.fetch_user(int(self.user_id))
                await NotificationManager.notifica_quantita_finita(user, alimento)
            
        except Exception as e:
            print(f"❌ Errore nella conferma scongelamento: {e}")
            import traceback
            traceback.print_exc()
            
            await interaction.followup.send(
                "❌ Si è verificato un errore. Riprova!",
                ephemeral=True
            )


class NotificationManager:
    """Manager per gestire le notifiche"""
    
    @staticmethod
    async def notifica_quantita_finita(user, alimento):
        """Invia notifica quando la quantità finisce"""
        try:
            embed = discord.Embed(
                title="⚠️ Alimento Quasi Terminato!",
                description=f"È rimasta solo 1 porzione di **{alimento['nome_alimento'].capitalize()}**!",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="🛒 Da comprare",
                value=f"{alimento['portion_to_buy']}g per {GIORNI[alimento['scongela_per_giorno']]}",
                inline=False
            )
            embed.add_field(
                name="💡 Suggerimento",
                value="Ricordati di fare la spesa prima che finisca!",
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
        
        print(f"🔔 Controllo reminder: {GIORNI[giorno_attuale]} alle {ora_formattata}")
        
        # Cerca tutti gli alimenti con reminder per oggi a quest'ora
        alimenti = DatabaseManager.get_alimenti_per_reminder(giorno_attuale, ora_formattata)
        
        for alimento in alimenti:
            # Controlla se già notificato oggi
            ultima_notifica = alimento.get('ultima_notifica')
            
            if ultima_notifica:
                ultima_data = datetime.fromisoformat(ultima_notifica)
                if ultima_data.date() == ora_attuale.date():
                    print(f"⏭️ {alimento['nome_alimento']} già notificato oggi")
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
                embed.add_field(
                    name="🛒 Grammi",
                    value=f"{alimento['portion_to_buy']}g",
                    inline=True
                )
                embed.set_footer(text="Clicca il bottone quando hai scongelato!")
                
                # Aggiungi la view con il bottone di conferma
                view = ConfermaScongelamentoView(alimento['id_univoco'], alimento['user_id'])
                
                await user.send(embed=embed, view=view)
                
                print(f"✅ Notifica inviata a {user.name} per {alimento['nome_alimento']}")
                
                # Aggiorna ultima notifica
                DatabaseManager.aggiorna_ultima_notifica(
                    alimento['_id'], 
                    ora_attuale.isoformat()
                )
                
            except discord.Forbidden:
                print(f"❌ Impossibile inviare DM a {alimento['user_id']}")
            except Exception as e:
                print(f"❌ Errore invio notifica: {e}")
                import traceback
                traceback.print_exc()
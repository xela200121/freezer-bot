# notifications.py
"""Sistema di notifiche e reminder con coda persistente"""

import discord
from datetime import datetime, timedelta
from database import DatabaseManager
from config import GIORNI


class ConfermaScongelamentoView(discord.ui.View):
    """View per confermare lo scongelamento dalla notifica"""
    def __init__(self, alimento_id, user_id):
        super().__init__(timeout=None) 
        self.alimento_id = alimento_id
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Ho Scongelato", style=discord.ButtonStyle.green, custom_id="conferma_scongelato")
    async def conferma_scongelato(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bottone per confermare lo scongelamento e diminuire la quantità"""
        try:
            await interaction.response.defer()
            
            alimento = DatabaseManager.get_alimento_by_id(self.user_id, self.alimento_id)
            
            if not alimento:
                await interaction.followup.send(
                    "❌ Alimento non trovato! Potrebbe essere stato eliminato.",
                    ephemeral=True
                )
                return
            
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
            
            if nuova_quantita == 1:
                embed.add_field(
                    name="⚠️ Attenzione",
                    value="È rimasta solo 1 porzione!\n🛒 Ricordati di comprarne altre.",
                    inline=False
                )
                embed.color = discord.Color.orange()
            
            if nuova_quantita == 0:
                embed.add_field(
                    name="🔴 Alimento Terminato",
                    value=f"Non ci sono più porzioni disponibili!\n🛒 Da comprare: {alimento['portion_to_buy']}g",
                    inline=False
                )
                embed.color = discord.Color.red()
            
            button.disabled = True
            button.label = "✅ Confermato"
            
            await interaction.edit_original_response(
                embed=embed,
                view=self
            )
            
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
    """Manager per gestire le notifiche con sistema di coda"""
    
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
            print(f"❌ Impossibile inviare DM a {user.id}")
        
    @staticmethod
    async def prepara_notifiche_giornaliere(bot):
        """Prepara le notifiche del giorno corrente (esegue a mezzanotte)"""
        oggi = datetime.now()
        giorno_oggi = oggi.weekday() + 1
        data_oggi = oggi.date()
        
        print(f"📅 Preparazione notifiche per {GIORNI[giorno_oggi]} ({data_oggi})")
        
        alimenti = DatabaseManager.get_alimenti_per_giorno(giorno_oggi)
        
        count = 0
        for alimento in alimenti:
            esiste = DatabaseManager.notifica_in_coda_esiste(
                alimento['_id'], 
                data_oggi.isoformat()
            )
            
            if not esiste:
                ora_reminder = alimento['reminder_hours'] 
                datetime_notifica = datetime.combine(
                    data_oggi, 
                    datetime.strptime(ora_reminder, "%H:%M").time()
                )
                
                success = DatabaseManager.crea_notifica_in_coda(
                    alimento_id=alimento['_id'],
                    user_id=alimento['user_id'],
                    alimento_nome=alimento['nome_alimento'],
                    data_notifica=data_oggi.isoformat(),
                    orario_notifica=ora_reminder,
                    datetime_notifica=datetime_notifica.isoformat()
                )
                
                if success:
                    count += 1
                    print(f"  ➕ Notifica preparata: {alimento['nome_alimento']} per user {alimento['user_id']}")
        
        print(f"✅ {count} notifiche preparate per oggi")
        
    @staticmethod
    async def elabora_coda_notifiche(bot):
        """Elabora la coda e invia le notifiche pronte"""
        ora_attuale = datetime.now()
        
        notifiche_da_inviare = DatabaseManager.get_notifiche_da_inviare(ora_attuale.isoformat())
        
        for notifica in notifiche_da_inviare:
            try:
                alimento = DatabaseManager.get_alimento_by_object_id(notifica['alimento_id'])
                
                if not alimento:
                    DatabaseManager.marca_notifica_come_fallita(
                        notifica['_id'], 
                        "Alimento non trovato"
                    )
                    continue
                
                if alimento['quantita'] <= 0:
                    DatabaseManager.marca_notifica_come_skipped(
                        notifica['_id'], 
                        "Quantità 0"
                    )
                    continue
                
                user = await bot.fetch_user(int(notifica['user_id']))
                
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
                
                view = ConfermaScongelamentoView(alimento['id_univoco'], alimento['user_id'])
                
                await user.send(embed=embed, view=view)
                
                DatabaseManager.marca_notifica_come_inviata(
                    notifica['_id'],
                    notifica['tentativi']
                )
                
                DatabaseManager.aggiorna_ultima_notifica(
                    alimento['_id'],
                    datetime.now().isoformat()
                )
                
                print(f"✅ Notifica inviata: {alimento['nome_alimento']} a {user.name}")
                
            except discord.Forbidden:
                DatabaseManager.incrementa_tentativi_notifica(
                    notifica['_id'],
                    "DM chiusi"
                )
                print(f"❌ DM chiusi per user {notifica['user_id']}")
                
            except Exception as e:
                DatabaseManager.incrementa_tentativi_notifica(
                    notifica['_id'],
                    str(e)
                )
                print(f"❌ Errore notifica: {e}")
        
        failed_count = DatabaseManager.marca_notifiche_failed_per_max_tentativi()
        if failed_count > 0:
            print(f"⚠️ {failed_count} notifiche marcate come failed (max tentativi raggiunto)")
    
    
    @staticmethod
    async def pulisci_notifiche_vecchie():
        """Rimuove notifiche più vecchie di 7 giorni"""
        deleted_count = DatabaseManager.elimina_notifiche_vecchie(giorni=7)
        print(f"🧹 Rimosse {deleted_count} notifiche vecchie")
    
    
    @staticmethod
    async def controlla_reminder(bot):
        """
        Metodo legacy per retrocompatibilità.
        Da rimuovere dopo il passaggio completo al sistema di coda.
        """
        print("⚠️ Metodo legacy controlla_reminder chiamato - considera di usare elabora_coda_notifiche")
        await NotificationManager.elabora_coda_notifiche(bot)
# voice_handler.py
"""Sistema di riconoscimento vocale GRATUITO con Vosk"""

import discord
import io
import json
import wave
import subprocess
from vosk import Model, KaldiRecognizer
import re
from datetime import datetime
from database import DatabaseManager
from models import AlimentoHelper
from config import GIORNI, GIORNI_INVERSO

# Il modello Vosk viene scaricato una volta e riutilizzato
VOSK_MODEL_PATH = "./vosk-model-small-it-0.22"  # Modello italiano


class VoiceHandler:
    """Handler per processare messaggi vocali con Vosk"""
    
    model = None  # Caricato una volta all'avvio
    
    @staticmethod
    def carica_modello():
        """Carica il modello Vosk"""
        try:
            if not VoiceHandler.model:
                print("📥 Caricamento modello Vosk italiano...")
                VoiceHandler.model = Model(VOSK_MODEL_PATH)
                print("✅ Modello Vosk caricato!")
        except Exception as e:
            print(f"❌ Errore caricamento modello Vosk: {e}")
            print("💡 Scarica il modello con: python download_vosk_model.py")
    
    @staticmethod
    async def processa_messaggio_vocale(message: discord.Message):
        """
        Processa un messaggio vocale per aggiungere un alimento.
        
        L'utente deve dire qualcosa come:
        "Aggiungi 3 porzioni di pollo da 150 grammi per lunedì alle 18"
        """
        try:
            # Verifica attachment audio
            if not message.attachments:
                return False
            
            attachment = message.attachments[0]
            
            if not attachment.content_type or not attachment.content_type.startswith('audio/'):
                return False
            
            print(f"🎤 Ricevuto messaggio vocale da {message.author.name}")
            
            # Invia typing indicator
            async with message.channel.typing():
                # Scarica l'audio
                audio_data = await attachment.read()
                
                # Trascrivi con Vosk
                transcript = await VoiceHandler.trascrivi_audio_vosk(audio_data, attachment.filename)
                
                if not transcript:
                    await message.reply("❌ Non sono riuscito a capire l'audio. Riprova parlando più chiaramente!")
                    return True
                
                print(f"📝 Trascrizione: {transcript}")
                
                # Invia trascrizione
                await message.reply(f"📝 Ho capito: *\"{transcript}\"*\n\n🔄 Sto elaborando...")
                
                # Estrai informazioni
                info = VoiceHandler.estrai_info_alimento(transcript)
                
                if not info:
                    await message.channel.send(
                        "❌ Non ho capito i dettagli dell'alimento.\n\n"
                        "💡 Prova a dire qualcosa come:\n"
                        "*'Aggiungi 3 porzioni di pollo da 150 grammi per lunedì alle 18'*"
                    )
                    return True
                
                # Mostra conferma
                await VoiceHandler.mostra_conferma_vocale(message, info)
                
            return True
            
        except Exception as e:
            print(f"❌ Errore processamento vocale: {e}")
            import traceback
            traceback.print_exc()
            
            await message.reply(
                "❌ Si è verificato un errore nel processare il messaggio vocale."
            )
            return True
    
    @staticmethod
    async def trascrivi_audio_vosk(audio_data: bytes, filename: str) -> str:
        """
        Trascrivi audio usando Vosk (completamente gratuito e offline).
        
        Vosk funziona meglio con audio WAV a 16kHz mono.
        Discord invia OGG/Opus, quindi convertiamo prima con ffmpeg.
        """
        try:
            # Salva temporaneamente l'audio
            temp_input = f"/tmp/{filename}"
            temp_wav = "/tmp/audio_converted.wav"
            
            with open(temp_input, 'wb') as f:
                f.write(audio_data)
            
            # Converti in WAV 16kHz mono con ffmpeg
            subprocess.run([
                'ffmpeg', '-i', temp_input,
                '-ar', '16000',  # Sample rate 16kHz
                '-ac', '1',      # Mono
                '-f', 'wav',
                temp_wav,
                '-y'  # Sovrascrivi se esiste
            ], check=True, capture_output=True)
            
            # Carica il modello (se non già caricato)
            if not VoiceHandler.model:
                VoiceHandler.carica_modello()
            
            if not VoiceHandler.model:
                print("❌ Modello Vosk non disponibile")
                return None
            
            # Apri il file WAV
            wf = wave.open(temp_wav, "rb")
            
            # Verifica che sia 16kHz mono
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                print(f"❌ Audio non compatibile: {wf.getnchannels()}ch, {wf.getsampwidth()}B, {wf.getframerate()}Hz")
                wf.close()
                return None
            
            # Crea recognizer
            rec = KaldiRecognizer(VoiceHandler.model, wf.getframerate())
            rec.SetWords(True)
            
            # Processa audio
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if 'text' in result:
                        results.append(result['text'])
            
            # Risultato finale
            final_result = json.loads(rec.FinalResult())
            if 'text' in final_result:
                results.append(final_result['text'])
            
            wf.close()
            
            # Unisci tutti i risultati
            transcript = ' '.join(results).strip()
            
            # Pulisci file temporanei
            import os
            try:
                os.remove(temp_input)
                os.remove(temp_wav)
            except:
                pass
            
            return transcript if transcript else None
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Errore ffmpeg: {e.stderr.decode() if e.stderr else e}")
            return None
        except Exception as e:
            print(f"❌ Errore trascrizione Vosk: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def estrai_info_alimento(testo: str) -> dict:
        """
        Estrae le informazioni dell'alimento dal testo trascritto.
        
        Esempi di input:
        - "aggiungi 3 porzioni di pollo da 150 grammi per lunedì alle 18"
        - "metti 2 petti di pollo 200 grammi martedì ore 17"
        - "5 porzioni pesce 120g giovedì 19:00"
        """
        testo = testo.lower()
        
        info = {
            "nome": None,
            "quantita": 1,
            "grammi": 150,
            "giorno": None,
            "orario": "18:00"
        }
        
        # 1. Estrai QUANTITÀ
        match_quantita = re.search(r'(\d+)\s*(?:porzioni?|pz|pezzi?)', testo)
        if match_quantita:
            info["quantita"] = int(match_quantita.group(1))
        else:
            match_num = re.search(r'^.*?(\d+)', testo)
            if match_num:
                info["quantita"] = int(match_num.group(1))
        
        # 2. Estrai GRAMMI
        match_grammi = re.search(r'(\d+)\s*(?:grammi?|gr?|g)\b', testo)
        if match_grammi:
            info["grammi"] = int(match_grammi.group(1))
        
        # 3. Estrai GIORNO
        for giorno_nome, giorno_num in GIORNI_INVERSO.items():
            if giorno_nome.lower() in testo:
                info["giorno"] = giorno_num
                break
        
        # 4. Estrai ORARIO
        match_orario = re.search(r'(?:alle|ore)?\s*(\d{1,2})[:.]?(\d{2})?', testo)
        if match_orario:
            ora = int(match_orario.group(1))
            minuti = match_orario.group(2) if match_orario.group(2) else "00"
            info["orario"] = f"{ora:02d}:{minuti}"
        
        # 5. Estrai NOME ALIMENTO
        testo_pulito = testo
        testo_pulito = re.sub(r'\d+\s*(?:porzioni?|pz|pezzi?|grammi?|gr?|g)\b', '', testo_pulito)
        
        for giorno in GIORNI_INVERSO.keys():
            testo_pulito = testo_pulito.replace(giorno.lower(), '')
        
        testo_pulito = re.sub(r'(?:alle|ore)\s*\d{1,2}[:.]?\d{0,2}', '', testo_pulito)
        
        parole_da_rimuovere = ['aggiungi', 'metti', 'inserisci', 'da', 'di', 'per', 'il']
        for parola in parole_da_rimuovere:
            testo_pulito = testo_pulito.replace(parola, '')
        
        nome_estratto = ' '.join(testo_pulito.split()).strip()
        
        if nome_estratto and len(nome_estratto) > 1:
            info["nome"] = nome_estratto
        
        # Validazione
        if not info["nome"] or not info["giorno"]:
            return None
        
        return info
    
    @staticmethod
    async def mostra_conferma_vocale(message: discord.Message, info: dict):
        """Mostra embed di conferma con bottoni"""
        from views import ConfermaAlimentoVocaleView
        
        embed = discord.Embed(
            title="🎤 Alimento da Messaggio Vocale",
            description="Ho estratto queste informazioni. Confermi?",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="🍖 Alimento", value=info["nome"].capitalize(), inline=True)
        embed.add_field(name="📦 Quantità", value=f"{info['quantita']} porzioni", inline=True)
        embed.add_field(name="⚖️ Grammi", value=f"{info['grammi']}g", inline=True)
        embed.add_field(name="📅 Giorno", value=GIORNI[info["giorno"]], inline=True)
        embed.add_field(name="🕐 Orario Reminder", value=info["orario"], inline=True)
        
        view = ConfermaAlimentoVocaleView(info, message.author.id)
        
        await message.channel.send(embed=embed, view=view)


# Aggiungi questa classe alla fine del file (o importala da views.py)
class ConfermaAlimentoVocaleView(discord.ui.View):
    """View per confermare l'alimento estratto dal vocale"""
    
    def __init__(self, info: dict, user_id: int):
        super().__init__(timeout=180)
        self.info = info
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Conferma e Aggiungi", style=discord.ButtonStyle.green)
    async def conferma(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            
            alimento_dict = AlimentoHelper.crea_alimento_dict(
                user_id=self.user_id,
                nome=self.info["nome"],
                quantita=self.info["quantita"],
                portion_to_buy=self.info["grammi"],
                giorno=self.info["giorno"],
                orario=self.info["orario"]
            )
            
            alimento_esistente = DatabaseManager.alimento_esiste(alimento_dict['id_univoco'])
            
            if alimento_esistente:
                DatabaseManager.incrementa_quantita_alimento(
                    alimento_dict['id_univoco'],
                    self.info["quantita"]
                )
                nuova_quantita = alimento_esistente['quantita'] + self.info["quantita"]
                
                embed = discord.Embed(
                    title="✅ Quantità Aggiornata!",
                    description=f"**{self.info['nome'].capitalize()}** già esistente. Quantità aggiornata!",
                    color=discord.Color.green()
                )
                embed.add_field(name="📦 Nuova Quantità", value=f"{nuova_quantita} porzioni", inline=True)
            else:
                DatabaseManager.inserisci_alimento_nuovo(alimento_dict)
                reminder_day = AlimentoHelper.calcola_reminder_day(self.info["giorno"])
                
                embed = discord.Embed(
                    title="✅ Alimento Aggiunto!",
                    description=f"**{self.info['nome'].capitalize()}** aggiunto al freezer!",
                    color=discord.Color.green()
                )
                embed.add_field(name="📦 Quantità", value=f"{self.info['quantita']} porzioni", inline=True)
                embed.add_field(name="📅 Per il giorno", value=GIORNI[self.info["giorno"]], inline=True)
                embed.add_field(name="📢 Reminder", value=f"{GIORNI[reminder_day]} alle {self.info['orario']}", inline=True)
            
            for item in self.children:
                item.disabled = True
            
            await interaction.edit_original_response(embed=embed, view=self)
            
        except Exception as e:
            print(f"❌ Errore conferma vocale: {e}")
            await interaction.followup.send("❌ Errore nel salvataggio. Riprova!", ephemeral=True)
    
    @discord.ui.button(label="❌ Annulla", style=discord.ButtonStyle.red)
    async def annulla(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = discord.Embed(
            title="❌ Operazione Annullata",
            description="Alimento non aggiunto.",
            color=discord.Color.red()
        )
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(embed=embed, view=self)
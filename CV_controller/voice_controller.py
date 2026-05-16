import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

def ascolta_microfono(coda_comandi):
    print("Cerco il modello italiano (se non c'è, lo scarico in automatico)...")
    
    modello = Model(lang="it")
    
    # --- L'OTTIMIZZAZIONE SUL VOCABOLARIO: 
    # Inserendo solo poche parole, non deve andare a cercare e a confrontarle con tutte quelle del modello ---
    
    vocabolario = '["pausa", "fuoco", "spara", "avvia", "gioco", "start", "[unk]"]'
    
    # Passiamo il vocabolario al riconoscitore
    riconoscitore = KaldiRecognizer(modello, 16000, vocabolario)
    
    coda_audio_interna = queue.Queue()
    
    def callback_microfono(indata, frames, time, status):
        coda_audio_interna.put(bytes(indata))

    print("🎤 Microfono AI in ascolto... (Comandi ottimizzati: 'Pausa', 'Fuoco', 'Spara', 'Avvia gioco')")
    
    # --- L'OTTIMIZZAZIONE SUL BLOCKSIZE:
    # Un blocksize più piccolo permette di processare l'audio più frequentemente, riducendo la latenza di riconoscimento.
    # Tuttavia, se riduciamo troppo il blocksize, andando meno di 4000, potremmo avere più risultati parziali e un carico maggiore sulla CPU.
    
    with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16',
                           channels=1, callback=callback_microfono):
        while True:
            dati = coda_audio_interna.get()
            
            # Leggiamo i risultati in tempo reale
            if riconoscitore.AcceptWaveform(dati):
                risultato = json.loads(riconoscitore.Result())
                testo = risultato.get("text", "")
            else:
                risultato = json.loads(riconoscitore.PartialResult())
                testo = risultato.get("partial", "")
                
            # --- CERCHIAMO LE PAROLE MAGICHE ---
            if "pausa" in testo:
                print(">>> Comando Vocale Riconosciuto: PAUSA")
                coda_comandi.put("PAUSA")
                riconoscitore.Reset()
            
            elif "fuoco" in testo or "spara" in testo:
                print(">>> Comando Vocale Riconosciuto: FUOCO 🔥")
                coda_comandi.put("FUOCO")
                riconoscitore.Reset()
                
            elif "avvia gioco" in testo or "start" in testo:
                print(">>> Comando Vocale Riconosciuto: AVVIA GIOCO ▶️")
                coda_comandi.put("AVVIA_GIOCO")
                riconoscitore.Reset()
                    
if __name__ == "__main__":
    print("Avvio il test del microfono...")
    coda_di_test = queue.Queue()
    ascolta_microfono(coda_di_test)
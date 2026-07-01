import json
import queue
import ssl
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# Disabilita la verifica SSL globale per consentire il download automatico del modello italiano di Vosk
ssl._create_default_https_context = ssl._create_unverified_context
try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    orig_get = requests.get
    requests.get = lambda *a, **k: orig_get(*a, **{**k, 'verify': False})
    
    orig_req = requests.Session.request
    requests.Session.request = lambda self, *a, **k: orig_req(self, *a, **{**k, 'verify': False})
    print("[INFO] Patch SSL applicata a 'requests'.")
except ImportError:
    pass


def ascolta_microfono(coda_comandi):
    """
    Ascolta continuamente dal microfono i comandi vocali in italiano
    e li invia alla coda condivisa con il gioco principale.
    """
    print("Cerco il modello italiano (se non c'è, lo scarico in automatico)...")
    modello = Model(lang="it")
    
    # Riconosce solo le parole nel vocabolario per evitare falsi positivi
    vocabolario = '["pausa", "fuoco", "spara", "avvia", "gioco", "start", "riprendi", "continua", "[unk]"]'
    riconoscitore = KaldiRecognizer(modello, 16000, vocabolario)
    
    coda_audio_interna = queue.Queue()
    
    def callback_microfono(indata, frames, time, status):
        coda_audio_interna.put(bytes(indata))
        
    print("Microfono AI in ascolto... (Comandi ottimizzati: 'Pausa', 'Riprendi', 'Fuoco', 'Spara', 'Avvia gioco')")
    
    with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16',
                           channels=1, callback=callback_microfono):
        while True:
            dati = coda_audio_interna.get()
            
            if riconoscitore.AcceptWaveform(dati):
                testo = json.loads(riconoscitore.Result()).get("text", "")
            else:
                testo = json.loads(riconoscitore.PartialResult()).get("partial", "")
                
            if "pausa" in testo:
                print(">>> Comando Vocale Riconosciuto: PAUSA")
                coda_comandi.put("PAUSA")
                riconoscitore.Reset()
            elif "fuoco" in testo or "spara" in testo:
                print(">>> Comando Vocale Riconosciuto: FUOCO")
                coda_comandi.put("FUOCO")
                riconoscitore.Reset()
            elif "riprendi" in testo or "continua" in testo:
                print(">>> Comando Vocale Riconosciuto: RIPRENDI")
                coda_comandi.put("RIPRENDI")
                riconoscitore.Reset()
            elif "avvia gioco" in testo or "start" in testo:
                print(">>> Comando Vocale Riconosciuto: AVVIA GIOCO")
                coda_comandi.put("AVVIA_GIOCO")
                riconoscitore.Reset()


if __name__ == "__main__":
    print("Avvio il test del microfono...")
    ascolta_microfono(queue.Queue())
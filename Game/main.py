import sys
import os
import multiprocessing as mp
import traceback

# --- CONFIGURAZIONE PERCORSI ---
cartella_corrente = os.path.dirname(os.path.abspath(__file__))
cartella_principale = os.path.dirname(cartella_corrente)
if cartella_principale not in sys.path:
    sys.path.append(cartella_principale)
    
from CV_controller import vision 
from CV_controller import voice_controller 
from core.Core import Core
       
if __name__ == '__main__':
    # Necessario per la gestione della grafica su macOS
    mp.set_start_method('spawn', force=True)

    print("=== AVVIO SUPER MARIO VISION MULTIMODALE ===")

    # 1. Creazione della coda condivisa
    coda_input_ai = mp.Queue()
    
    # 2. Avvio del Processo VISIONE
    print("Avvio tracciamento corpo...")
    processo_visione = mp.Process(target=vision.avvia_telecamera, args=(coda_input_ai,), daemon=True)
    processo_visione.start()
    
    # 3. Avvio del Processo VOCE 
    print("Avvio riconoscimento vocale...")
    processo_voce = mp.Process(target=voice_controller.ascolta_microfono, args=(coda_input_ai,), daemon=True)
    processo_voce.start()
    
    # 4. Avvio del GIOCO 
    print("Inizializzazione motore di gioco...")
    try:
        oCore = Core(coda_ai=coda_input_ai) 
        oCore.main_loop()
    except Exception as e:
        print("\n❌ ERRORE CRITICO NEL GIOCO:")
        traceback.print_exc()
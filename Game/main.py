import sys
import os
import multiprocessing as mp
import traceback

# --- INIZIALIZZAZIONE PATH ---
cartella_corrente = os.path.dirname(os.path.abspath(__file__))
cartella_principale = os.path.dirname(cartella_corrente)
if cartella_principale not in sys.path:
    sys.path.append(cartella_principale)


from CV_controller import vision 
from core.Core import Core       

if __name__ == '__main__':
    mp.set_start_method('spawn', force=True)

    print("1. Creazione della Coda...")
    coda_input_ai = mp.Queue()
    
    print("2. Avvio del processo della webcam...")
    processo_visione = mp.Process(target=vision.avvia_telecamera, args=(coda_input_ai,), daemon=True)
    processo_visione.start()
    
    print("3. Inizializzazione di Pygame...")
    try:
        # Proviamo ad avviare il gioco
        oCore = Core(coda_ai=coda_input_ai) 
        print("4. Avvio del ciclo principale di Mario...")
        oCore.main_loop()
    except Exception as e:
        # Se Pygame crasha, lo catturiamo qui!
        print("\n" + "="*50)
        print("❌ ERRORE NEL GIOCO PYGAME:")
        traceback.print_exc()
        print("="*50 + "\n")
import sys
import os
import queue
import threading

# Aggiungiamo la cartella principale al path per permettere l'importazione
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from CV_controller.voice_controller import ascolta_microfono

def main():
    print("==================================================")
    print(" TESTER TRASCRIZIONE VOCALE (Vocabolario Ristretto)")
    print("==================================================")
    print("Parole riconosciute: pausa, fuoco, spara, avvia gioco, start")
    print("Premi CTRL+C per uscire.")
    print("Avvio del motore vocale in corso...\n")
    
    # Coda di comunicazione (la stessa "cassetta della posta" che usa Super Mario)
    coda_comandi = queue.Queue()
    
    # Avviamo il riconoscimento vocale in un processo parallelo (Thread)
    thread_voce = threading.Thread(target=ascolta_microfono, args=(coda_comandi,), daemon=True)
    thread_voce.start()
    
    try:
        # Loop infinito che "ascolta" la coda
        while True:
            # .get() mette il programma in pausa finché non arriva un messaggio nella coda
            comando = coda_comandi.get()
            
            # Trascrizione a schermo
            print(f"\n[TRASCRIZIONE] --> Hai attivato il comando: {comando}")
            
    except KeyboardInterrupt:
        print("\nTest terminato. Arrivederci!")

if __name__ == "__main__":
    main()

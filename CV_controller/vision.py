import cv2
import mediapipe as mp
import time 

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

telecamera = cv2.VideoCapture(0)

# --- VARIABILI DI CALIBRAZIONE ---
# Questo è il Flag: 1: Calibrazione Riposo, 2: Calibrazione Salto, 0: Gioco Attivo
in_calibrazione = 1
# Cronometro per la calibrazione
inizio_tempo = time.time() 
somma_altezze = 0
conteggio_frame = 0

altezza_riposo = 0
salto_massimo = 0


# --- VARIABILI DEL GIOCO (SPRINT) ---
passi_sprint = 0
tempo_ultimo_passo = time.time()
tempo_ultimo_salto = time.time()

print("Sistema avviato. Mettiti in posizione per la calibrazione (5 secondi)!")

while True:
    success, frame = telecamera.read()
    if not success: 
        continue

    # Flippiamo l'immagine per un effetto specchio
    frame = cv2.flip(frame, 1)
    # Convertiamo l'immagine da BGR a RGB per MediaPipe e OpenCV
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(img_rgb)

    if results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        
        # Estraiamo le spalle
        spalla_dx = results.pose_landmarks.landmark[11]
        spalla_sx = results.pose_landmarks.landmark[12]
        altezza_media = (spalla_dx.y + spalla_sx.y) / 2
        
        # Estraggo il naso per avere un riferimento stabile
        # Mi servirà per capire se l'utente andrà a destra, sinistra o rimarrà centrale
        naso = results.pose_landmarks.landmark[0]
        posizione_naso = ["Centro", "Destra", "Sinistra"]

        # --- LOGICA DI CALIBRAZIONE PER LO SPRINT ---
        if in_calibrazione == 1:
            # Calcoliamo quanti secondi sono passati
            tempo_trascorso = time.time() - inizio_tempo
            
            if tempo_trascorso < 5.0: 
                # Raccogliamo i dati per 5 secondi
                somma_altezze += altezza_media
                conteggio_frame += 1
                cv2.putText(frame, f"Calibrazione... {5 - int(tempo_trascorso)}s", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            else:
                # Finiti i 5 secondi, calcoliamo la media definitiva
                altezza_riposo = somma_altezze / conteggio_frame
                in_calibrazione = 2
                # Resettiamo il cronometro dei passi prima di iniziare a giocare
                inizio_tempo = time.time() 
                print(f"✅ Calibrazione completata! Altezza di riposo: {altezza_riposo:.4f}")
        
        # --- LOGICA DI CALIBRAZIONE PER IL SALTO ---
        elif in_calibrazione == 2:
            tempo_trascorso = time.time() - inizio_tempo
            delta_spalle = altezza_riposo - altezza_media
            
            # Catturiamo il picco massimo del salto
            if delta_spalle > salto_massimo:
                salto_massimo = delta_spalle

            if tempo_trascorso < 5.0:
                cv2.putText(frame, f"2. FAI UN BEL SALTO! ... {5 - int(tempo_trascorso)}s", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                cv2.putText(frame, f"Salto Max registrato: {salto_massimo:.3f}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            else:
                # Sicurezza: se per caso l'utente non ha saltato, c'è un minimo di default
                if salto_massimo < 0.15:
                    salto_massimo = 0.15
                in_calibrazione = 0 # Entriamo nel gioco!
                tempo_ultimo_passo = time.time()
                print(f"✅ Salto completato! Salto Max: {salto_massimo:.4f}")
                
        
        # --- GIOCO ATTIVO ---
        else:
            # PER FAR CAPIRE ALL'UTENTE CHE IL SISTEMA È ATTIVO E PER GUIDARLO NELLE DIREZIONI,
            # DISEGNO FASCE E TRACCIAMENTO ASSE X (DESTRA/SINISTRA)
            h, w, _ = frame.shape
            overlay = frame.copy()
            
            # Disegno i 3 rettangoli trasparenti (Sinistra, Centro, Destra - divisi in terzi)
            cv2.rectangle(overlay, (0, 0), (int(w * 0.33), h), (0, 0, 255), -1)   # Rosso
            cv2.rectangle(overlay, (int(w * 0.33), 0), (int(w * 0.66), h), (0, 255, 0), -1) # Verde
            cv2.rectangle(overlay, (int(w * 0.66), 0), (w, h), (255, 0, 0), -1)   # Blu
            
            # Fondo l'overlay con il frame reale al 20% di opacità
            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

            # Estraggo il naso e calcolo la direzione
            naso = results.pose_landmarks.landmark[0]
            if naso.x < 0.33:
                direzione = "SINISTRA <--"
            elif naso.x > 0.66:
                direzione = "--> DESTRA"
            else:
                direzione = "ZONA MORTA (FERMO)"
                
            # Stampo la direzione in alto a destra
            cv2.putText(frame, direzione, (w - 300, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # LOGICA DI RILEVAMENTO SALTO E CORSA
            
            delta_spalle = altezza_riposo - altezza_media
            
            # Calcoliamo le soglie dinamiche basate sul tuo salto_massimo
            soglia_salto = salto_massimo * 0.75       # Il salto scatta se raggiungi il 75% del tuo salto massimo
            tetto_corsa = salto_massimo * 0.50        # La corsa viene rilevata solo se NON superi il 50% del salto

            stato = "Camminata normale"
            colore = (0, 255, 0) # Verde

            # 1. RILEVAMENTO SALTO (Ha la priorità sulla corsa)
            if delta_spalle >= soglia_salto:
                if (time.time() - tempo_ultimo_salto) > 1.0: # Cooldown di 1 secondo
                    stato = "SALTO !!!"
                    colore = (0, 0, 255) # Rosso
                    tempo_ultimo_salto = time.time()
            
            # 2. RILEVAMENTO CORSA (Solo se non stiamo saltando)
            else:
                if time.time() - tempo_ultimo_passo > 1.0:
                    passi_sprint = 0

                # Delta > 0.04 (ignora respiro) e Delta < tetto_corsa (ignora salti)
                if 0.04 < delta_spalle < tetto_corsa: 
                    if time.time() - tempo_ultimo_passo > 0.1:
                        passi_sprint += 1
                        tempo_ultimo_passo = time.time()

                if passi_sprint >= 3:
                    stato = "SPRINT ATTIVO !!!"
                    colore = (0, 165, 255) # Arancione

            # Stampa a schermo
            cv2.putText(frame, stato, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, colore, 2)
            cv2.putText(frame, f"Passi combo: {passi_sprint} | Delta: {delta_spalle:.3f}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Soglia Salto: >{soglia_salto:.2f} | Tetto Corsa: <{tetto_corsa:.2f}", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow('Test AI Mario', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

telecamera.release()
cv2.destroyAllWindows()
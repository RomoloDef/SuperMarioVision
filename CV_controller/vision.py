import cv2
import mediapipe as mp
import time # IMPORT FONDAMENTALE PER IL CRONOMETRO

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

# --- VARIABILI DI CALIBRAZIONE ---
in_calibrazione = True
inizio_tempo = time.time() # Cronometro per la calibrazione
somma_altezze = 0
conteggio_frame = 0
altezza_riposo = 0

# --- VARIABILI DEL GIOCO (SPRINT) ---
passi_sprint = 0
tempo_ultimo_passo = time.time()

print("Sistema avviato. Mettiti in posizione per la calibrazione (5 secondi)!")

while True:
    success, frame = cap.read()
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

        # --- LOGICA DI CALIBRAZIONE ---
        if in_calibrazione:
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
                in_calibrazione = False
                # Resettiamo il cronometro dei passi prima di iniziare a giocare
                tempo_ultimo_passo = time.time() 
                print(f"✅ Calibrazione completata! Altezza di riposo: {altezza_riposo:.4f}")
        
        # --- GIOCO ATTIVO ---
        else:
            # 1. Calcolo del Delta dinamico
            delta_spalle = altezza_riposo - altezza_media

            # 2. Il Cronometro di Reset: se ti fermi per più di 1 secondo, azzera la combo
            if time.time() - tempo_ultimo_passo > 1.0:
                passi_sprint = 0

            # 3. Rilevamento del singolo passo 
            # (Delta > 0.04 ignora il respiro, Delta < 0.15 ignora i salti veri e propri)
            if 0.04 < delta_spalle < 0.15: 
                # Debounce: aspetta almeno 0.1s tra un passo e l'altro per non contare i frame doppi
                if time.time() - tempo_ultimo_passo > 0.1:
                    passi_sprint += 1
                    tempo_ultimo_passo = time.time()

            # 4. Attivazione dello stato nel gioco
            if passi_sprint >= 3:
                stato = "SPRINT ATTIVO !!!"
                colore = (0, 165, 255) # Arancione
            else:
                stato = "Camminata normale"
                colore = (0, 255, 0) # Verde

            # Stampa a schermo per il test
            cv2.putText(frame, stato, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, colore, 2)
            cv2.putText(frame, f"Passi combo: {passi_sprint} | Delta: {delta_spalle:.3f}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow('Test AI Mario', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
import cv2
import mediapipe as mp
import time
import os
import urllib.request
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- 1. DEFINIZIONE MANUALE DELLE CONNESSIONI ---
# Poiché mp.solutions non è disponibile in questa versione, definiamo qui quali punti collegare
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16), # Spalle e braccia
    (11, 23), (12, 24), (23, 24),                   # Busto
    (23, 25), (24, 26), (25, 27), (26, 28)          # Gambe
]

def download_model(model_path):
    """Scarica il modello pre-addestrato se non presente."""
    if not os.path.exists(model_path):
        print(f"Scaricamento modello in corso: {model_path}...")
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
        try:
            urllib.request.urlretrieve(url, model_path)
            print("✅ Modello scaricato con successo!")
        except Exception as e:
            print(f"❌ Errore durante il download: {e}")

def disegna_scheletro_manuale(frame, landmarks):
    """Disegna manualmente i punti e le connessioni della posa usando solo OpenCV."""
    h, w, _ = frame.shape
    # Disegna connessioni
    for start_idx, end_idx in POSE_CONNECTIONS:
        if start_idx < len(landmarks) and end_idx < len(landmarks):
            lm1 = landmarks[start_idx]
            lm2 = landmarks[end_idx]
            # Disegna solo se i punti hanno una visibilità minima
            if lm1.visibility > 0.5 and lm2.visibility > 0.5:
                p1 = (int(lm1.x * w), int(lm1.y * h))
                p2 = (int(lm2.x * w), int(lm2.y * h))
                cv2.line(frame, p1, p2, (0, 255, 0), 2)
    
    # Disegna i punti principali (Naso e Spalle)
    for i in [0, 11, 12]:
        if i < len(landmarks):
            lm = landmarks[i]
            if lm.visibility > 0.5:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)

def avvia_telecamera(coda_comandi):
    # --- 2. CONFIGURAZIONE MEDIAPIPE 0.10.35 (TASKS API) ---
    model_path = 'pose_landmarker_lite.task'
    download_model(model_path)

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False
    )
    
    detector = vision.PoseLandmarker.create_from_options(options)
    telecamera = cv2.VideoCapture(0)

    # --- VARIABILI DI CALIBRAZIONE ---
    in_calibrazione = 1
    inizio_tempo = time.time() 
    somma_altezze = 0
    conteggio_frame = 0

    altezza_riposo = 0
    salto_massimo = 0

    # --- VARIABILI DEL GIOCO (SPRINT) ---
    passi_sprint = 0
    tempo_ultimo_passo = time.time()
    tempo_ultimo_salto = time.time()
    
    # Variabile per il calcolo sicuro del tempo richiesto da MediaPipe
    conteggio_frame_totali = 0 

    print("Sistema AI (v0.10.35) avviato. Mettiti in posizione per la calibrazione!")

    while True:
        success, frame = telecamera.read()
        if not success: 
            continue

        frame = cv2.flip(frame, 1)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # MediaPipe 0.10 richiede un oggetto mp.Image specifico
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        
        # Calcolo timestamp per RunningMode.VIDEO
        conteggio_frame_totali += 1
        timestamp_ms = conteggio_frame_totali * 33 

        # Rilevamento pose
        results = detector.detect_for_video(mp_image, timestamp_ms)

        if results.pose_landmarks:
            # Estrazione primo set di landmarks (lista di oggetti, non protobuf)
            pose_landmarks = results.pose_landmarks[0]
            
            # Disegno manuale dello scheletro
            disegna_scheletro_manuale(frame, pose_landmarks)
            
            # --- LOGICA DEL GIOCO ---
            spalla_dx = pose_landmarks[11]
            spalla_sx = pose_landmarks[12]
            altezza_media = (spalla_dx.y + spalla_sx.y) / 2
            
            naso = pose_landmarks[0]

            # --- LOGICA DI CALIBRAZIONE PER LO SPRINT ---
            if in_calibrazione == 1:
                tempo_trascorso = time.time() - inizio_tempo
                
                if tempo_trascorso < 5.0: 
                    somma_altezze += altezza_media
                    conteggio_frame += 1
                    cv2.putText(frame, f"Calibrazione... {5 - int(tempo_trascorso)}s", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                else:
                    altezza_riposo = somma_altezze / (conteggio_frame if conteggio_frame > 0 else 1)
                    in_calibrazione = 2
                    inizio_tempo = time.time() 
                    print(f"✅ Calibrazione completata! Altezza di riposo: {altezza_riposo:.4f}")
            
            # --- LOGICA DI CALIBRAZIONE PER IL SALTO ---
            elif in_calibrazione == 2:
                tempo_trascorso = time.time() - inizio_tempo
                delta_spalle = altezza_riposo - altezza_media
                
                if delta_spalle > salto_massimo:
                    salto_massimo = delta_spalle

                if tempo_trascorso < 5.0:
                    cv2.putText(frame, f"2. FAI UN BEL SALTO! ... {5 - int(tempo_trascorso)}s", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                    cv2.putText(frame, f"Salto Max registrato: {salto_massimo:.3f}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                else:
                    if salto_massimo < 0.15:
                        salto_massimo = 0.15
                    in_calibrazione = 0
                    tempo_ultimo_passo = time.time()
                    print(f"✅ Salto completato! Salto Max: {salto_massimo:.4f}")
                    
            # --- GIOCO ATTIVO ---
            else:
                h, w, _ = frame.shape
                overlay = frame.copy()
                
                cv2.rectangle(overlay, (0, 0), (int(w * 0.33), h), (0, 0, 255), -1)   
                cv2.rectangle(overlay, (int(w * 0.33), 0), (int(w * 0.66), h), (0, 255, 0), -1) 
                cv2.rectangle(overlay, (int(w * 0.66), 0), (w, h), (255, 0, 0), -1)   
                cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

                # --- 1. COMANDI ASSE X (DESTRA/SINISTRA) ---
                if naso.x < 0.33:
                    direzione = "SINISTRA <--"
                    coda_comandi.put("SINISTRA")
                elif naso.x > 0.66:
                    direzione = "--> DESTRA"
                    coda_comandi.put("DESTRA")
                else:
                    direzione = "ZONA MORTA (FERMO)"
                    coda_comandi.put("FERMO_X")
                    
                cv2.putText(frame, direzione, (w - 300, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                # --- 2. COMANDI ASSE Y (SALTO/CORSA) ---
                delta_spalle = altezza_riposo - altezza_media
                soglia_salto = salto_massimo * 0.75       
                tetto_corsa = salto_massimo * 0.50        

                stato = "Camminata normale"
                colore = (0, 255, 0) 

                if delta_spalle >= soglia_salto:
                    if (time.time() - tempo_ultimo_salto) > 1.0: 
                        stato = "SALTO !!!"
                        colore = (0, 0, 255) 
                        coda_comandi.put("SALTO")
                        tempo_ultimo_salto = time.time()
                else:
                    if time.time() - tempo_ultimo_passo > 1.0:
                        passi_sprint = 0

                    if 0.04 < delta_spalle < tetto_corsa: 
                        if time.time() - tempo_ultimo_passo > 0.1:
                            passi_sprint += 1
                            tempo_ultimo_passo = time.time()

                    if passi_sprint >= 3:
                        stato = "SPRINT ATTIVO !!!"
                        colore = (0, 165, 255) 
                        coda_comandi.put("SPRINT")
                    else:
                        coda_comandi.put("CAMMINA")

                cv2.putText(frame, stato, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, colore, 2)
                cv2.putText(frame, f"Passi combo: {passi_sprint} | Delta: {delta_spalle:.3f}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Soglia Salto: >{soglia_salto:.2f} | Tetto Corsa: <{tetto_corsa:.2f}", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow('Test AI Mario', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    telecamera.release()
    cv2.destroyAllWindows()
    detector.close()

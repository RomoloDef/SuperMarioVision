import cv2
import mediapipe as mp
import time
import os
import urllib.request
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from .gestures import predict_gesture
    from .signal_filters import PoseFilter
except (ImportError, ValueError):
    try:
        from gestures import predict_gesture  # type:ignore[import]
        from signal_filters import PoseFilter  # type:ignore[import]
    except ImportError:
        from CV_controller.gestures import predict_gesture
        from CV_controller.signal_filters import PoseFilter

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
    
    # Inizializza filtro
    pose_filter = PoseFilter(filter_type='kalman')

    # --- VARIABILI DI STATISTICHE E LATENZA ---
    # Latency tracking
    prev_time = time.time()
    latency_ms = 0
    conteggio_frame_totali = 0

    print("Sistema AI (v0.10.35) avviato con Classificatore Gestures.")

    while True:
        loop_start = time.time()
        success, frame = telecamera.read()
        if not success: 
            continue

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        conteggio_frame_totali += 1
        timestamp_ms = conteggio_frame_totali * 33 

        # Rilevamento pose
        results = detector.detect_for_video(mp_image, timestamp_ms)
        if results.pose_landmarks:
            pose_landmarks = results.pose_landmarks[0]
            # Applicazione FILTRO
            pose_landmarks = pose_filter.filter(pose_landmarks)
            # Disegno manuale dello scheletro
            disegna_scheletro_manuale(frame, pose_landmarks)
            
            # --- CLASSIFICAZIONE GESTI ---
            gesto, confidence = predict_gesture(pose_landmarks)
            
            # FALLBACK SE MODELLO MANCANTE (Logica Manuale Semplice)
            model_loaded = confidence > 0 or gesto != "unknown"
            if not model_loaded:
                # Logica basata su posizione naso e spalle (fallback)
                naso = pose_landmarks[0]
                spalla_dx = pose_landmarks[11]
                spalla_sx = pose_landmarks[12]
                y_spalle = (spalla_dx.y + spalla_sx.y) / 2
                
                if naso.x < 0.4: gesto = "sinistra"
                elif naso.x > 0.6: gesto = "destra"
                elif y_spalle < 0.45: gesto = "salto"
                else: gesto = "fermo"
                confidence = 0.5

            # --- LOGICA DI COMANDO BASATA SU CLASSIFICATORE ---
            if gesto == "sinistra":
                coda_comandi.put("SINISTRA")
                colore_feedback = (255, 0, 0)
            elif gesto == "destra":
                coda_comandi.put("DESTRA")
                colore_feedback = (0, 0, 255)
            elif gesto == "salto":
                coda_comandi.put("SALTO")
                colore_feedback = (0, 255, 255)
            elif gesto == "sprint":
                coda_comandi.put("SPRINT")
                colore_feedback = (0, 165, 255)
            else:
                coda_comandi.put("FERMO_X")
                coda_comandi.put("CAMMINA")
                colore_feedback = (0, 255, 0)

            # Overlay HUD
            cv2.rectangle(frame, (10, 10), (450, 150), (0, 0, 0), -1)
            cv2.putText(frame, f"GESTO: {gesto.upper()}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, colore_feedback, 2)
            if not model_loaded:
                cv2.putText(frame, "ATTENZIONE: MODELLO AI MANCANTE", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                cv2.putText(frame, "(Uso fallback manuale)", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            else:
                cv2.putText(frame, f"CONF: {confidence:.2f}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            cv2.putText(frame, f"LATENCY: {latency_ms:.1f}ms", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        else:
            # Messaggio se non rileva il corpo
            cv2.putText(frame, "NESSUN CORPO RILEVATO", (w//2 - 150, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Calcolo latenza
        latency_ms = (time.time() - loop_start) * 1000
        
        cv2.imshow('SuperMarioVision - AI Controller', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            print(">>> Invio comando AVVIA_GIOCO...")
            coda_comandi.put("AVVIA_GIOCO")

    telecamera.release()
    cv2.destroyAllWindows()
    detector.close()

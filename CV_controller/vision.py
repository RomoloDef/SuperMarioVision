import cv2
import mediapipe as mp
import time
from collections import deque
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

# --- 2. CONFIGURAZIONE ZONE E BRACCIA ---
ZONA_SINISTRA_MAX = 0.33   # Confine: da 0% a 33% → zona sinistra
ZONA_DESTRA_MIN = 0.67     # Confine: da 67% a 100% → zona destra
SOGLIA_BRACCIO = 0.10       # Distanza minima polso-spalla per "braccio alzato" (normalizzata)

# --- 3. CONFIGURAZIONE SALTO FISICO ---
SOGLIA_SALTO = 0.03         # Spostamento verticale minimo delle spalle per triggerare un salto
COOLDOWN_SALTO_MS = 500     # Tempo minimo tra due salti consecutivi (ms)
FINESTRA_SALTO = 10         # Numero di frame nel buffer per il calcolo del delta


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


def disegna_zone(frame, zona_attiva=None):
    """
    Disegna le 3 zone colorate semi-trasparenti sulla finestra della telecamera.
    La zona attiva viene evidenziata con opacità maggiore.
    
    Zone:
        - Sinistra (0% - 33%): blu
        - Centro (33% - 67%): verde
        - Destra (67% - 100%): rosso
    """
    h, w, _ = frame.shape
    confine_sx = int(w * ZONA_SINISTRA_MAX)
    confine_dx = int(w * ZONA_DESTRA_MIN)

    # Colori zone (BGR)
    COLORE_SX = (255, 150, 50)     # Blu chiaro
    COLORE_CENTRO = (50, 220, 50)  # Verde
    COLORE_DX = (50, 50, 255)      # Rosso

    # Disegna tutte le zone con opacità base bassa
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (confine_sx, h), COLORE_SX, -1)
    cv2.rectangle(overlay, (confine_sx, 0), (confine_dx, h), COLORE_CENTRO, -1)
    cv2.rectangle(overlay, (confine_dx, 0), (w, h), COLORE_DX, -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    # Evidenzia la zona attiva con opacità extra
    if zona_attiva:
        overlay_attivo = frame.copy()
        if zona_attiva == 'sinistra':
            cv2.rectangle(overlay_attivo, (0, 0), (confine_sx, h), COLORE_SX, -1)
        elif zona_attiva == 'centro':
            cv2.rectangle(overlay_attivo, (confine_sx, 0), (confine_dx, h), COLORE_CENTRO, -1)
        elif zona_attiva == 'destra':
            cv2.rectangle(overlay_attivo, (confine_dx, 0), (w, h), COLORE_DX, -1)
        cv2.addWeighted(overlay_attivo, 0.18, frame, 0.82, 0, frame)

    # Linee di confine bianche tra le zone
    cv2.line(frame, (confine_sx, 0), (confine_sx, h), (255, 255, 255), 2)
    cv2.line(frame, (confine_dx, 0), (confine_dx, h), (255, 255, 255), 2)

    # Etichette zone in basso
    label_y = h - 15
    cv2.putText(frame, "<< SINISTRA", (10, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    centro_x = confine_sx + (confine_dx - confine_sx) // 2 - 40
    cv2.putText(frame, "FERMO", (centro_x, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, "DESTRA >>", (confine_dx + 10, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def rileva_braccio_alzato(landmarks, lato):
    """
    Rileva se un braccio è alzato confrontando la posizione Y del polso con la spalla.
    
    Parametri:
        landmarks: lista dei 33 landmark di MediaPipe
        lato: 'destro' o 'sinistro' (dal punto di vista dell'UTENTE)
    
    Nota: dopo cv2.flip(frame, 1), i landmark MediaPipe sono invertiti:
        - Braccio DESTRO utente → landmark 11 (spalla), 15 (polso)
        - Braccio SINISTRO utente → landmark 12 (spalla), 16 (polso)
    
    Restituisce True se il polso è significativamente sopra la spalla.
    """
    if lato == 'destro':
        spalla = landmarks[11]  # MP: LEFT_SHOULDER → Spalla DX utente (dopo flip)
        polso = landmarks[15]   # MP: LEFT_WRIST → Polso DX utente (dopo flip)
    else:
        spalla = landmarks[12]  # MP: RIGHT_SHOULDER → Spalla SX utente (dopo flip)
        polso = landmarks[16]   # MP: RIGHT_WRIST → Polso SX utente (dopo flip)

    # y=0 è in alto, y=1 è in basso → polso sopra la spalla = polso.y < spalla.y
    # Verifichiamo anche la visibilità per evitare falsi positivi
    return (polso.y < (spalla.y - SOGLIA_BRACCIO) 
            and polso.visibility > 0.5 
            and spalla.visibility > 0.5)


def avvia_telecamera(coda_comandi):
    # --- CONFIGURAZIONE MEDIAPIPE 0.10.35 (TASKS API) ---
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
    
    # Inizializza filtro di Kalman per la stabilizzazione
    pose_filter = PoseFilter(filter_type='kalman')

    # --- VARIABILI DI STATO ---
    latency_ms = 0
    conteggio_frame_totali = 0

    # Salto fisico: buffer circolare delle posizioni Y delle spalle
    storico_y_spalle = deque(maxlen=FINESTRA_SALTO)
    cooldown_salto = 0  # Timestamp dell'ultimo salto (ms)

    # Edge detection per sprint (braccio sinistro)
    braccio_sx_precedente = False

    print("Sistema AI Ibrido avviato (ML per Zone + Salto Fisico + Sprint Braccio).")

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

        # --- RILEVAMENTO POSE ---
        results = detector.detect_for_video(mp_image, timestamp_ms)

        zona_attiva = None
        salto_rilevato = False
        braccio_sx_alzato = False
        model_loaded = False
        confidence = 0.0

        if results.pose_landmarks:
            pose_landmarks = results.pose_landmarks[0]
            # Applicazione filtro di Kalman per ridurre il jitter
            pose_landmarks = pose_filter.filter(pose_landmarks)

            # ═══════════════════════════════════════════════════
            # CANALE 1: ZONA DI MOVIMENTO (Classificatore ML)
            # ═══════════════════════════════════════════════════
            gesto, confidence = predict_gesture(pose_landmarks)
            model_loaded = confidence > 0 or gesto != "unknown"

            if model_loaded and gesto in ('sinistra', 'centro', 'destra'):
                # Il classificatore ML ha riconosciuto una zona valida
                zona_attiva = gesto
            else:
                # Fallback geometrico: usiamo la posizione X del naso
                naso = pose_landmarks[0]
                if naso.x < ZONA_SINISTRA_MAX:
                    zona_attiva = 'sinistra'
                elif naso.x > ZONA_DESTRA_MIN:
                    zona_attiva = 'destra'
                else:
                    zona_attiva = 'centro'
                if not model_loaded:
                    confidence = 0.5

            # ═══════════════════════════════════════════════════
            # CANALE 2: SALTO FISICO (Movimento Verticale)
            # ═══════════════════════════════════════════════════
            # Calcoliamo la media Y delle spalle (dopo flip: 11=DX utente, 12=SX utente)
            y_spalle = (pose_landmarks[11].y + pose_landmarks[12].y) / 2
            storico_y_spalle.append(y_spalle)

            if len(storico_y_spalle) >= 5:
                # Confrontiamo la posizione attuale con la media dei frame precedenti
                valori_precedenti = list(storico_y_spalle)[:-1]  # Tutti tranne l'ultimo
                media_precedente = sum(valori_precedenti) / len(valori_precedenti)
                delta = media_precedente - y_spalle  # Positivo = corpo sale (y diminuisce)

                tempo_corrente = time.time() * 1000
                if delta > SOGLIA_SALTO and (tempo_corrente - cooldown_salto) > COOLDOWN_SALTO_MS:
                    salto_rilevato = True
                    cooldown_salto = tempo_corrente

            # ═══════════════════════════════════════════════════
            # CANALE 3: SPRINT (Braccio Sinistro)
            # ═══════════════════════════════════════════════════
            braccio_sx_alzato = rileva_braccio_alzato(pose_landmarks, 'sinistro')

            # --- INVIO COMANDI MOVIMENTO (ogni frame) ---
            if zona_attiva == 'sinistra':
                coda_comandi.put("SINISTRA")
            elif zona_attiva == 'destra':
                coda_comandi.put("DESTRA")
            else:  # centro → fermo
                coda_comandi.put("FERMO_X")

            # --- INVIO COMANDO SALTO (impulso singolo con cooldown) ---
            if salto_rilevato:
                coda_comandi.put("SALTO")

            # --- INVIO COMANDI SPRINT (edge detection braccio sinistro) ---
            if braccio_sx_alzato and not braccio_sx_precedente:
                coda_comandi.put("SPRINT")
            elif not braccio_sx_alzato and braccio_sx_precedente:
                coda_comandi.put("CAMMINA")

            # Aggiorna stato precedente per il prossimo frame
            braccio_sx_precedente = braccio_sx_alzato

        # --- DISEGNO ZONE (sempre visibili, anche senza corpo rilevato) ---
        disegna_zone(frame, zona_attiva)

        # --- DISEGNO SCHELETRO E HUD ---
        if results.pose_landmarks:
            disegna_scheletro_manuale(frame, pose_landmarks)

            # HUD — Pannello informativo in alto a sinistra
            cv2.rectangle(frame, (10, 10), (380, 125), (0, 0, 0), -1)
            cv2.rectangle(frame, (10, 10), (380, 125), (80, 80, 80), 1)

            # Zona attiva con colore corrispondente
            colore_zona = {
                'sinistra': (255, 150, 50),
                'centro': (50, 220, 50),
                'destra': (50, 50, 255)
            }
            cv2.putText(frame, f"ZONA: {zona_attiva.upper()}", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                       colore_zona.get(zona_attiva, (255, 255, 255)), 2)

            # Stato salto e sprint
            colore_salto = (0, 255, 255) if salto_rilevato else (120, 120, 120)
            colore_sx = (0, 165, 255) if braccio_sx_alzato else (120, 120, 120)
            testo_salto = "SALTO!" if salto_rilevato else "---"
            testo_sx = "SPRINT!" if braccio_sx_alzato else "---"
            cv2.putText(frame, f"Salto: {testo_salto}", (20, 68),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, colore_salto, 1)
            cv2.putText(frame, f"Sprint: {testo_sx}", (20, 93),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, colore_sx, 1)

            # Info modello ML
            if not model_loaded:
                cv2.putText(frame, "[Fallback geometrico]", (20, 115),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            else:
                cv2.putText(frame, f"ML conf: {confidence:.2f}", (20, 115),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        else:
            # Messaggio se non rileva il corpo
            cv2.putText(frame, "NESSUN CORPO RILEVATO", (w // 2 - 180, h // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Latenza (sempre visibile, in alto a destra)
        latency_ms = (time.time() - loop_start) * 1000
        cv2.putText(frame, f"LAT: {latency_ms:.0f}ms", (w - 140, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

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

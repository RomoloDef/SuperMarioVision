import cv2
import mediapipe as mp
import time
from collections import deque
import os
import urllib.request
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

try:
    from gestures import predict_gesture
    from signal_filters import PoseFilter
except ImportError:
    from CV_controller.gestures import predict_gesture
    from CV_controller.signal_filters import PoseFilter

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28)
]

ZONA_SINISTRA_MAX = 0.33
ZONA_DESTRA_MIN = 0.67
SOGLIA_BRACCIO = 0.10
SOGLIA_SALTO = 0.03
COOLDOWN_SALTO_MS = 500
FINESTRA_SALTO = 10


def download_model(model_path):
    """Scarica il modello di tracciamento MediaPipe Pose Landmarker se non presente."""
    if not os.path.exists(model_path):
        print(f"Scaricamento modello {model_path}...")
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
        try:
            urllib.request.urlretrieve(url, model_path)
            print("✅ Modello scaricato con successo!")
        except Exception as e:
            print(f"❌ Errore durante il download del modello: {e}")


def disegna_scheletro_manuale(frame, landmarks):
    """Disegna sul frame i segmenti che uniscono i landmark corporei rilevati."""
    h, w, _ = frame.shape
    for start_idx, end_idx in POSE_CONNECTIONS:
        if start_idx < len(landmarks) and end_idx < len(landmarks):
            lm1, lm2 = landmarks[start_idx], landmarks[end_idx]
            if lm1.visibility > 0.5 and lm2.visibility > 0.5:
                cv2.line(frame, (int(lm1.x * w), int(lm1.y * h)), (int(lm2.x * w), int(lm2.y * h)), (0, 255, 0), 2)
    
    for i in [0, 11, 12]:
        if i < len(landmarks) and landmarks[i].visibility > 0.5:
            cv2.circle(frame, (int(landmarks[i].x * w), int(landmarks[i].y * h)), 5, (255, 255, 255), -1)


def disegna_zone(frame, zona_attiva=None):
    """Disegna le tre aree verticali per indicare all'utente i comandi associati."""
    h, w, _ = frame.shape
    confine_sx = int(w * ZONA_SINISTRA_MAX)
    confine_dx = int(w * ZONA_DESTRA_MIN)

    colore_sx = (255, 150, 50)
    colore_centro = (50, 220, 50)
    colore_dx = (50, 50, 255)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (confine_sx, h), colore_sx, -1)
    cv2.rectangle(overlay, (confine_sx, 0), (confine_dx, h), colore_centro, -1)
    cv2.rectangle(overlay, (confine_dx, 0), (w, h), colore_dx, -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    if zona_attiva:
        overlay_attivo = frame.copy()
        if zona_attiva == 'sinistra':
            cv2.rectangle(overlay_attivo, (0, 0), (confine_sx, h), colore_sx, -1)
        elif zona_attiva == 'centro':
            cv2.rectangle(overlay_attivo, (confine_sx, 0), (confine_dx, h), colore_centro, -1)
        elif zona_attiva == 'destra':
            cv2.rectangle(overlay_attivo, (confine_dx, 0), (w, h), colore_dx, -1)
        cv2.addWeighted(overlay_attivo, 0.18, frame, 0.82, 0, frame)

    cv2.line(frame, (confine_sx, 0), (confine_sx, h), (255, 255, 255), 2)
    cv2.line(frame, (confine_dx, 0), (confine_dx, h), (255, 255, 255), 2)
    
    cv2.putText(frame, "<< SINISTRA", (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, "FERMO", (confine_sx + 20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, "DESTRA >>", (confine_dx + 10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def rileva_braccio_alzato(landmarks, lato):
    """Rileva se un braccio specifico dell'utente è alzato."""
    spalla = landmarks[11 if lato == 'destro' else 12]
    polso = landmarks[15 if lato == 'destro' else 16]
    return polso.y < (spalla.y - SOGLIA_BRACCIO) and polso.visibility > 0.5 and spalla.visibility > 0.5


def avvia_telecamera(coda_comandi):
    """
    Inizializza la fotocamera e processa i frame video in tempo reale per
    estrarre comandi di movimento, salti e sprint da inviare alla coda del gioco.
    """
    model_path = 'pose_landmarker_lite.task'
    download_model(model_path)

    """
    Tramite la modalità video, MediaPipe non analizza frame da zero, ma tiene in memoria i 
    frame precedenti per traciare meglio i movimenti.
    Le soglie sono state impostate a 0.5 cosi che se è sicuro al 50% che ci sia una persona, 
    il sistema cercherà di rilevarla.
    """
    detector = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,                          
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
    )
    
    # Accensione webcam
    telecamera = cv2.VideoCapture(0)
    pose_filter = PoseFilter()
    storico_y_spalle = deque(maxlen=FINESTRA_SALTO)
    
    cooldown_salto = 0
    braccio_sx_precedente = False
    conteggio_frame = 0

    print("Sistema AI Ibrido avviato (ML per Zone + Salto Fisico + Sprint Braccio).")

    while True:
        loop_start = time.time()
        success, frame = telecamera.read()
        if not success: continue

        # L'immagine viene specchiata per far si che i movimenti intuitivi dell'utente
        # siano percepiti correttamente dalla camera. Cosi se l'utente muove la mano destra, 
        # la camera la vedrà come destra, ma in realta è sinistra.
        
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        conteggio_frame += 1

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        results = detector.detect_for_video(mp_image, conteggio_frame * 33)

        zona_attiva = None
        salto_rilevato = False
        braccio_sx_alzato = False

        if results.pose_landmarks:
            landmarks = pose_filter.filter(results.pose_landmarks[0])

            # Classificazione orizzontale (ML con Fallback geometrico)
            gesto, confidence = predict_gesture(landmarks)
            if confidence > 0 or gesto != "unknown":
                zona_attiva = gesto
            else:
                naso = landmarks[0]
                if naso.x < ZONA_SINISTRA_MAX:
                    zona_attiva = 'sinistra'
                elif naso.x > ZONA_DESTRA_MIN:
                    zona_attiva = 'destra'
                else:
                    zona_attiva = 'centro'

            # --- RILEVAMENTO SALTO ---
            y_spalle = (landmarks[11].y + landmarks[12].y) / 2
            storico_y_spalle.append(y_spalle)
            
            if len(storico_y_spalle) >= 5:
                valori_prec = list(storico_y_spalle)[:-1]
                media_prec = sum(valori_prec) / len(valori_prec)
                tempo_ms = time.time() * 1000
                
                # Se c'è uno spostamento rapido verso l'alto (riduzione di Y)
                if (media_prec - y_spalle) > SOGLIA_SALTO and (tempo_ms - cooldown_salto) > COOLDOWN_SALTO_MS:
                    salto_rilevato = True
                    cooldown_salto = tempo_ms

            # --- RILEVAMENTO SPRINT ---
            braccio_sx_alzato = rileva_braccio_alzato(landmarks, 'sinistro')

            # --- INVIO COMANDI ALLA CODA ---
            coda_comandi.put("SINISTRA" if zona_attiva == 'sinistra' else "DESTRA" if zona_attiva == 'destra' else "FERMO_X")
            
            if salto_rilevato:
                coda_comandi.put("SALTO")
                
            if braccio_sx_alzato and not braccio_sx_precedente:
                coda_comandi.put("SPRINT")
            elif not braccio_sx_alzato and braccio_sx_precedente:
                coda_comandi.put("CAMMINA")
            
            braccio_sx_precedente = braccio_sx_alzato

        # --- RENDERING GRAFICO E HUD ---
        disegna_zone(frame, zona_attiva)
        
        if results.pose_landmarks:
            disegna_scheletro_manuale(frame, landmarks)
            
            cv2.rectangle(frame, (10, 10), (300, 95), (0, 0, 0), -1)
            cv2.putText(frame, f"ZONA: {str(zona_attiva).upper()}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Salto: {'SI' if salto_rilevato else 'NO'}", (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, f"Sprint: {'SI' if braccio_sx_alzato else 'NO'}", (20, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "NESSUN CORPO RILEVATO", (w // 2 - 150, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        lat = (time.time() - loop_start) * 1000
        cv2.putText(frame, f"LAT: {lat:.0f}ms", (w - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow('SuperMarioVision - AI Controller', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            coda_comandi.put("AVVIA_GIOCO")

    telecamera.release()
    cv2.destroyAllWindows()
    detector.close()



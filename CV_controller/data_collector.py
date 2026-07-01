import cv2
import mediapipe as mp
import csv
import os
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import cv2
import mediapipe as mp
import csv
import os
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = 'pose_landmarker_lite.task'
OUTPUT_CSV = 'gesture_dataset.csv'
GESTI = ['sinistra', 'centro', 'destra']
FRAMES_PER_GESTO = 300
SECONDI_PREPARAZIONE = 3
ZONA_SINISTRA_MAX = 0.33
ZONA_DESTRA_MIN = 0.67

HEADER = ['label'] + [f'{c}{i}' for i in range(33) for c in ['x', 'y', 'z', 'v']]


def disegna_zone(frame, zona_target=None):
    """
    Disegna sullo schermo tre aree verticali colorate semitrasparenti (sinistra, centro, destra)
    per indicare all'utente dove posizionarsi.
    """
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

    if zona_target:
        overlay_attivo = frame.copy()
        if zona_target == 'sinistra':
            cv2.rectangle(overlay_attivo, (0, 0), (confine_sx, h), colore_sx, -1)
        elif zona_target == 'centro':
            cv2.rectangle(overlay_attivo, (confine_sx, 0), (confine_dx, h), colore_centro, -1)
        elif zona_target == 'destra':
            cv2.rectangle(overlay_attivo, (confine_dx, 0), (w, h), colore_dx, -1)
        cv2.addWeighted(overlay_attivo, 0.18, frame, 0.82, 0, frame)

    cv2.line(frame, (confine_sx, 0), (confine_sx, h), (255, 255, 255), 2)
    cv2.line(frame, (confine_dx, 0), (confine_dx, h), (255, 255, 255), 2)
    
    cv2.putText(frame, "<< SINISTRA", (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, "CENTRO", (confine_sx + 20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, "DESTRA >>", (confine_dx + 10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def raccolta_gesto(detector, telecamera, label, frame_counter_start):
    """
    Gestisce la raccolta dati per un singolo gesto, includendo una fase di countdown
    per posizionarsi e la successiva acquisizione dei landmark corporei.
    """
    righe = []
    frame_raccolti = 0
    conteggio_frame = frame_counter_start

    # Fase di countdown
    inizio_prep = time.time()
    print(f"\n>>> Preparati per il gesto: '{label.upper()}' <<<")
    
    while True:
        success, frame = telecamera.read()
        if not success: continue
        frame = cv2.flip(frame, 1)
        
        tempo_rimasto = SECONDI_PREPARAZIONE - (time.time() - inizio_prep)
        if tempo_rimasto <= 0:
            break

        disegna_zone(frame, label)
        cv2.putText(frame, f"Posizionati in: {label.upper()}", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(frame, f"Inizio tra: {int(tempo_rimasto) + 1}s", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.imshow('Raccolta Dati - SuperMarioVision', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None, conteggio_frame

    # Fase di registrazione dei frame
    print(f"    Registrazione in corso...")
    while frame_raccolti < FRAMES_PER_GESTO:
        success, frame = telecamera.read()
        if not success: continue
        frame = cv2.flip(frame, 1)
        conteggio_frame += 1
        
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        results = detector.detect_for_video(mp_image, conteggio_frame * 33)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks[0]
            row = [label]
            for lm in landmarks:
                row.extend([round(lm.x, 6), round(lm.y, 6), round(lm.z, 6), round(lm.visibility, 6)])
            righe.append(row)
            frame_raccolti += 1

        disegna_zone(frame, label)
        cv2.putText(frame, f"REC: {label.upper()}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        cv2.putText(frame, f"{frame_raccolti}/{FRAMES_PER_GESTO} frame", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imshow('Raccolta Dati - SuperMarioVision', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None, conteggio_frame

    print(f"    [OK] '{label}': {frame_raccolti} frame raccolti.")
    return righe, conteggio_frame


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"[ERRORE] Modello non trovato: {MODEL_PATH}")
        return

    file_nuovo = not os.path.exists(OUTPUT_CSV)
    csv_file = open(OUTPUT_CSV, 'a', newline='')
    writer = csv.writer(csv_file)

    if file_nuovo:
        writer.writerow(HEADER)
        print(f"[INFO] Nuovo dataset creato: {OUTPUT_CSV}")
    else:
        print(f"[INFO] Aggiunta dati a dataset esistente: {OUTPUT_CSV}")

    detector = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
    )
    
    telecamera = cv2.VideoCapture(0)
    if not telecamera.isOpened():
        print("[ERRORE] Webcam non trovata.")
        return

    conteggio_frame_totali = 0
    for gesto in GESTI:
        righe, conteggio_frame_totali = raccolta_gesto(detector, telecamera, gesto, conteggio_frame_totali)
        if righe is None:
            print("\n[ATTENZIONE] Raccolta interrotta.")
            break
        writer.writerows(righe)
        csv_file.flush()

    csv_file.close()
    telecamera.release()
    cv2.destroyAllWindows()
    detector.close()


if __name__ == '__main__':
    main()
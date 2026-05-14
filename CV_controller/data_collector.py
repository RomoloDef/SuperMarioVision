import cv2
import mediapipe as mp
import csv
import os
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CONFIGURAZIONE ---
MODEL_PATH = 'pose_landmarker_lite.task'
OUTPUT_CSV = 'gesture_dataset.csv'

# Gesti da raccogliere e quanti frame per gesto
GESTI = ['fermo', 'sinistra', 'destra', 'salto', 'sprint']
FRAMES_PER_GESTO = 300   # ~10 secondi a 30fps — puoi aumentare
SECONDI_PREPARAZIONE = 3  # Tempo per mettersi in posizione prima della registrazione

# Colonne del CSV
HEADER = ['label']
for i in range(33):
    HEADER += [f'x{i}', f'y{i}', f'z{i}', f'v{i}']


def inizializza_detector():
    """Inizializza MediaPipe PoseLandmarker in modalità VIDEO."""
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False
    )
    return vision.PoseLandmarker.create_from_options(options)


def landmark_to_row(label, landmarks):
    """
    Converte una lista di 33 landmark in una riga CSV.
    Ogni landmark ha: x, y, z (normalizzati 0-1) e visibility.
    """
    row = [label]
    for lm in landmarks:
        row += [
            round(lm.x, 6),
            round(lm.y, 6),
            round(lm.z, 6),
            round(lm.visibility, 6)
        ]
    return row


def raccolta_gesto(detector, telecamera, label, frame_counter_start):
    """
    Raccoglie FRAMES_PER_GESTO frame per un singolo gesto.
    Restituisce la lista di righe da scrivere nel CSV.
    """
    righe = []
    frame_raccolti = 0
    conteggio_frame = frame_counter_start

    # --- Fase 1: countdown di preparazione ---
    inizio_prep = time.time()
    print(f"\n>>> Preparati per il gesto: '{label.upper()}' <<<")
    print(f"    Hai {SECONDI_PREPARAZIONE} secondi per metterti in posizione...")

    while True:
        success, frame = telecamera.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        tempo_rimasto = SECONDI_PREPARAZIONE - (time.time() - inizio_prep)

        if tempo_rimasto <= 0:
            break

        # Overlay countdown
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        cv2.putText(frame, f"Gesto: {label.upper()}", (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
        cv2.putText(frame, f"Inizio tra: {int(tempo_rimasto) + 1}s", (50, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(frame, "Premi Q per uscire", (50, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        cv2.imshow('Raccolta Dati - SuperMarioVision', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None, conteggio_frame  # segnale di uscita

    # --- Fase 2: registrazione ---
    print(f"    Registrazione in corso... ({FRAMES_PER_GESTO} frame)")
    inizio_rec = time.time()

    while frame_raccolti < FRAMES_PER_GESTO:
        success, frame = telecamera.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

        conteggio_frame += 1
        timestamp_ms = conteggio_frame * 33

        results = detector.detect_for_video(mp_image, timestamp_ms)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks[0]
            righe.append(landmark_to_row(label, landmarks))
            frame_raccolti += 1

        # HUD di registrazione
        progresso = int((frame_raccolti / FRAMES_PER_GESTO) * (frame.shape[1] - 100))
        cv2.rectangle(frame, (50, frame.shape[0] - 60),
                      (frame.shape[1] - 50, frame.shape[0] - 35), (50, 50, 50), -1)
        cv2.rectangle(frame, (50, frame.shape[0] - 60),
                      (50 + progresso, frame.shape[0] - 35), (0, 220, 0), -1)
        cv2.putText(frame, f"REC  {label.upper()}", (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        cv2.putText(frame, f"{frame_raccolti}/{FRAMES_PER_GESTO} frame", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, "Premi Q per uscire", (50, frame.shape[0] - 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        cv2.imshow('Raccolta Dati - SuperMarioVision', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None, conteggio_frame

    print(f"    ✅ '{label}': {frame_raccolti} frame raccolti.")
    return righe, conteggio_frame


def main():
    # Controlla se il modello esiste
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Modello non trovato: {MODEL_PATH}")
        print("   Assicurati di avere pose_landmarker_lite.task nella stessa cartella.")
        return

    # Apri/crea il CSV
    file_gia_esistente = os.path.exists(OUTPUT_CSV)
    csv_file = open(OUTPUT_CSV, 'a', newline='')
    writer = csv.writer(csv_file)

    if not file_gia_esistente:
        writer.writerow(HEADER)
        print(f"📄 Nuovo dataset creato: {OUTPUT_CSV}")
    else:
        print(f"📄 Dataset esistente trovato: aggiunta dati a {OUTPUT_CSV}")

    detector = inizializza_detector()
    telecamera = cv2.VideoCapture(0)

    if not telecamera.isOpened():
        print("❌ Webcam non trovata.")
        return

    print("\n" + "="*50)
    print("  RACCOLTA DATI - SuperMarioVision")
    print("="*50)
    print(f"  Gesti da raccogliere: {GESTI}")
    print(f"  Frame per gesto:      {FRAMES_PER_GESTO}")
    print(f"  Output:               {OUTPUT_CSV}")
    print("="*50)
    print("  Premi Q in qualsiasi momento per interrompere.\n")

    conteggio_frame_totali = 0

    for gesto in GESTI:
        righe, conteggio_frame_totali = raccolta_gesto(
            detector, telecamera, gesto, conteggio_frame_totali
        )

        if righe is None:
            print("\n⚠️  Raccolta interrotta dall'utente.")
            break

        writer.writerows(righe)
        csv_file.flush()  # Salva subito su disco — sicurezza in caso di crash

    csv_file.close()
    telecamera.release()
    cv2.destroyAllWindows()
    detector.close()

    # Riepilogo finale
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, 'r') as f:
            totale_righe = sum(1 for _ in f) - 1  # -1 per l'header
        print(f"\n✅ Raccolta completata!")
        print(f"   Totale campioni nel dataset: {totale_righe}")
        print(f"   File salvato in: {OUTPUT_CSV}")


if __name__ == '__main__':
    main()
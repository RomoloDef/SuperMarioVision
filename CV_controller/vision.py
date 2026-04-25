import cv2
import mediapipe as mp

# Inizializziamo in modo leggero e sicuro per Mac: Impostazioni utili per evitare problemi di compatibilità e prestazioni
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# Inizializziamo la telecamera 
telecamera = cv2.VideoCapture(0)
print("Ambiente avviato. Premi 'q' per uscire.")

while True:
    successo, frame = telecamera.read()
    if not successo:
        continue
    
    # Flippiamo l'immagine per una visualizzazione più naturale (come uno specchio)
    frame = cv2.flip(frame, 1)
    # Convertiamo l'immagine da BGR a RGB per OpenCV e MediaPipe
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    results = pose.process(img_rgb)

    # Disegniamo i punti di riferimento del corpo se sono stati rilevati
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            frame, 
            results.pose_landmarks, 
            mp_pose.POSE_CONNECTIONS
        )

    # Mostriamo il frame con i punti di riferimento disegnati
    cv2.imshow('Test AI Mario', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Rilasciamo la telecamera e chiudiamo tutte le finestre
telecamera.release()
cv2.destroyAllWindows()
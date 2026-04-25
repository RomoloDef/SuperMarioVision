import cv2
import mediapipe as mp

# Definisco la variabile per la webcam
telecamera = cv2.VideoCapture(0)

# Inizializzo mediapipe per il rilevamento del corpo umano
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_disegno = mp.solutions.drawing_utils # Serve per disegnare i punti e le linee

# Utilizzo un ciclo infinito per leggere continuamente i frame dalla webcam
while True:
    successo, frame = telecamera.read()
    if not successo:
        break

    # Faccio specchiare l'immagine per renderla naturale (effetto specchio)
    frame = cv2.flip(frame, 1)

    # Conversione colori per MediaPipe (da BGR a RGB)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # L'IA analizza il corpo
    risultati = pose.process(frame_rgb)
    
    # Se l'IA trova un corpo, disegna lo scheletro sul frame
    if risultati.pose_landmarks:
        mp_disegno.draw_landmarks(
            frame, 
            risultati.pose_landmarks, 
            mp_pose.POSE_CONNECTIONS
        )
    
    # MOSTRA l'immagine finale (con lo scheletro sopra)
    cv2.imshow("Webcam Super Mario - AI Test", frame)
    
    # Esce se premi 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Rilascio la webcam e chiudo tutte le finestre
telecamera.release()
cv2.destroyAllWindows()
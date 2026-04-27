import cv2
import mediapipe as mp
import time 

def avvia_telecamera(coda_comandi):
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

    print("Sistema AI avviato. Mettiti in posizione per la calibrazione (5 secondi)!")

    while True:
        success, frame = telecamera.read()
        if not success: 
            continue

        frame = cv2.flip(frame, 1)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(img_rgb)

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            spalla_dx = results.pose_landmarks.landmark[11]
            spalla_sx = results.pose_landmarks.landmark[12]
            altezza_media = (spalla_dx.y + spalla_sx.y) / 2
            
            naso = results.pose_landmarks.landmark[0]

            # --- LOGICA DI CALIBRAZIONE PER LO SPRINT ---
            if in_calibrazione == 1:
                tempo_trascorso = time.time() - inizio_tempo
                
                if tempo_trascorso < 5.0: 
                    somma_altezze += altezza_media
                    conteggio_frame += 1
                    cv2.putText(frame, f"Calibrazione... {5 - int(tempo_trascorso)}s", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                else:
                    altezza_riposo = somma_altezze / conteggio_frame
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
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import os

# Definisci il percorso del CSV (assumendo che lo script sia dentro testing_models)
csv_path = '../gesture_dataset.csv'

if not os.path.exists(csv_path):
    # Prova a cercarlo nella cartella corrente se eseguito dalla root
    csv_path = 'gesture_dataset.csv'
    if not os.path.exists(csv_path):
        print("Errore: File dataset non trovato.")
        exit(1)

print("Caricamento dataset...")
df = pd.read_csv(csv_path)

# Estraiamo solo le coordinate (rimuoviamo la colonna testuale 'label')
X_raw = df.drop(columns=['label']).values

print(f"\nDimensione della matrice: {X_raw.shape[0]} righe x {X_raw.shape[1]} colonne")

print("\n" + "="*50)
print(" DATI GREZZI (Prima dello StandardScaler)")
print("="*50)
print("Guardiamo i primi 5 valori del PRIMO frame registrato:")
print("(Esempio: Coordinata X, Y, Z e Visibilita del naso...)")
print(X_raw[0, :5])

print("\nApplichiamo StandardScaler.fit_transform(X)...")
scaler = StandardScaler()
# L'oggetto scaler analizza tutte le colonne, calcola la media e la varianza per ciascuna, 
# e poi trasforma i numeri.
X_scaled = scaler.fit_transform(X_raw)

print("\n" + "="*50)
print(" DATI SCALATI (Dopo lo StandardScaler)")
print("="*50)
print("Guardiamo gli STESSI 5 valori del PRIMO frame, ora trasformati:")
print(X_scaled[0, :5])

print("\n" + "="*50)
print(" LA MATEMATICA DIETRO LE QUINTE")
print("="*50)
print("Prendiamo la Colonna 0 (la primissima coordinata di tutto il dataset):")
print(f"Media Originale:  {np.mean(X_raw[:, 0]):.6f}")
print(f"Varianza Orig.:   {np.var(X_raw[:, 0]):.6f}")
print(f"---")
print(f"Media Scalata:    {np.mean(X_scaled[:, 0]):.6f}  (Praticamente ZERO)")
print(f"Varianza Scalata: {np.var(X_scaled[:, 0]):.6f}  (Esattamente UNO)")

print("\nCONCLUSIONE:")
print("Lo StandardScaler ha 'schiacciato' e 'spostato' l'intero dataset in modo che")
print("ogni colonna abbia esattamente Media = 0 e Varianza = 1.")
print("Senza questo step, numeri molto grandi in una coordinata avrebbero 'schiacciato'")
print("il peso di numeri piu' piccoli, confondendo la Rete Neurale e l'SVM!")

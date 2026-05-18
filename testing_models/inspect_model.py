import pickle
import os
import sys

# Cerchiamo il file del modello (nella root)
model_path = '../models/best_model.pkl'

if not os.path.exists(model_path):
    model_path = 'models/best_model.pkl'
    if not os.path.exists(model_path):
        print(f"Errore: File best_model.pkl non trovato. Esegui prima 'make train' per generarlo!")
        sys.exit(1)

# Apriamo il file in modalita di LETTURA BINARIA ('rb')
with open(model_path, 'rb') as f:
    pipeline = pickle.load(f)

print("="*50)
print(" CONTENUTO DEL FILE PICKLE (LA PIPELINE)")
print("="*50)

print(f"Tipo di oggetto principale: {type(pipeline)}")
print(f"Step salvati al suo interno: {list(pipeline.named_steps.keys())}\n")

# ---------------------------------------------------------
# 1. ESPLORIAMO LO SCALER
# ---------------------------------------------------------
scaler = pipeline.named_steps['scaler']
print("--- 1. LO STANDARD SCALER ---")
print(f"Numero totale di coordinate imparate: {scaler.n_features_in_}")
print("Medie calcolate dal tuo training (mostro solo le prime 5):")
print(scaler.mean_[:5])
print("Varianze calcolate dal tuo training (mostro solo le prime 5):")
print(scaler.var_[:5])
print("\n")

# ---------------------------------------------------------
# 2. ESPLORIAMO IL MODELLO
# ---------------------------------------------------------
clf = pipeline.named_steps['clf']
print("--- 2. IL MODELLO DI MACHINE LEARNING ---")
tipo_modello = type(clf).__name__
print(f"Tipo di intelligenza: {tipo_modello}")
print(f"Classi previste (identificativi): {clf.classes_}\n")

if tipo_modello == 'MLPClassifier':
    print(">> E' una Rete Neurale (Multi-Layer Perceptron) <<")
    print(f"Numero di layer totali: {clf.n_layers_}")
    print(f"Numero di iterazioni di studio fatte (Epoche): {clf.n_iter_}")
    
    print("\nEcco la cosa piu affascinante: le griglie dei 'Pesi' (Weights)!")
    print("Questi sono i moltiplicatori che il modello ha imparato per collegare i layer:")
    for i, matrice in enumerate(clf.coefs_):
        print(f"  - Matrice {i}: collega {matrice.shape[0]} neuroni a {matrice.shape[1]} neuroni. Contiene {matrice.size} numeri!")
        
    print("\nEsempio di 5 pesi a caso estratti dal primo layer:")
    print(clf.coefs_[0][0][:5])

elif tipo_modello == 'SVC':
    print(">> E' una Support Vector Machine (SVM) <<")
    print(f"Parametri matematici: C={clf.C}, Kernel={clf.kernel}")
    print(f"Numero totale di Support Vectors geometrici trovati: {clf.support_.shape[0]}")
    
    print("\nEsempio delle coordinate di un Support Vector puro:")
    print(clf.support_vectors_[0][:5])

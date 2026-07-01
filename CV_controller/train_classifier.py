import pandas as pd
import numpy as np
import pickle
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.pipeline import Pipeline

CSV_PATH = 'gesture_dataset.csv'
OUTPUT_DIR = 'models'


def main():
    if not os.path.exists(CSV_PATH):
        print(f"[ERRORE] Dataset non trovato: {CSV_PATH}. Esegui prima la raccolta dati.")
        return

    # 1. Caricamento e preprocessing
    print("[INFO] Caricamento dataset...")
    df = pd.read_csv(CSV_PATH)
    print(f"   Totale campioni: {len(df)}")
    print(f"   Distribuzione:\n{df['label'].value_counts().to_string()}\n")

    X = df.drop(columns=['label']).values.astype(np.float32)
    y = df['label'].values

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    print(f"   Classi: {list(le.classes_)}")

    # Split train/test (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )
    print(f"   Train: {len(X_train)} | Test: {len(X_test)} campioni\n")

    # 2. Definizione Modelli
    modelli = {
        'svm': Pipeline([
            ('scaler', StandardScaler()),
            ('clf', SVC(kernel='rbf', C=10, probability=True, random_state=42))
        ]),
        'mlp': Pipeline([
            ('scaler', StandardScaler()),
            ('clf', MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, early_stopping=True, random_state=42))
        ])
    }

    risultati = {}
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 3. Addestramento e Valutazione
    for nome, pipeline in modelli.items():
        print(f"\n==================================================\n  Modello: {nome.upper()}\n==================================================")
        
        # Cross-validation
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5)
        print(f"  Cross-val accuracy (5-fold): {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

        # Training e Test
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        
        accuracy = (y_pred == y_test).mean()
        risultati[nome] = accuracy
        print(f"  Test accuracy: {accuracy:.3f}\n")
        print(classification_report(y_test, y_pred, target_names=le.classes_))

        # Salvataggio modello singolo e confusion matrix
        model_path = os.path.join(OUTPUT_DIR, f'{nome}.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(pipeline, f)
        print(f"  [OK] Modello salvato: {model_path}")

        cm = confusion_matrix(y_test, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le.classes_)
        disp.plot(cmap='Blues')
        plt.title(f'Confusion Matrix - {nome.upper()}')
        cm_path = os.path.join(OUTPUT_DIR, f'confusion_matrix_{nome}.png')
        plt.savefig(cm_path, dpi=150)
        plt.close()
        print(f"  [OK] Confusion matrix salvata: {cm_path}")

    # Salva label encoder
    encoder_path = os.path.join(OUTPUT_DIR, 'label_encoder.pkl')
    with open(encoder_path, 'wb') as f:
        pickle.dump(le, f)
    print(f"  [OK] Encoder salvato: {encoder_path}")

    # 4. Selezione e salvataggio modello migliore
    migliore_nome = max(risultati, key=risultati.get)
    best_path = os.path.join(OUTPUT_DIR, 'best_model.pkl')
    with open(best_path, 'wb') as f:
        pickle.dump(modelli[migliore_nome], f)

    print(f"\n==================================================\n  Modello migliore: {migliore_nome.upper()} (accuracy: {risultati[migliore_nome]:.3f})")
    print(f"  Salvato come: {best_path}\n==================================================")


if __name__ == '__main__':
    main()
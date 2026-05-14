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
from sklearn.metrics import (
    classification_report, confusion_matrix, ConfusionMatrixDisplay
)
from sklearn.pipeline import Pipeline

# --- CONFIGURAZIONE ---
CSV_PATH    = 'gesture_dataset.csv'
OUTPUT_DIR  = 'models'
RANDOM_SEED = 42


# ─────────────────────────────────────────
# 1. CARICAMENTO E PREPROCESSING
# ─────────────────────────────────────────

def carica_dataset(csv_path):
    print("📂 Caricamento dataset...")
    df = pd.read_csv(csv_path)

    print(f"   Totale campioni: {len(df)}")
    print(f"   Distribuzione gesti:\n{df['label'].value_counts().to_string()}\n")

    # Controlla campioni sbilanciati (avvisa se uno ha meno del 70% della media)
    counts = df['label'].value_counts()
    media = counts.mean()
    for gesto, n in counts.items():
        if n < media * 0.7:
            print(f"   ⚠️  '{gesto}' ha pochi campioni ({n}). "
                  f"Considera di raccogliere altri dati.")

    X = df.drop(columns=['label']).values.astype(np.float32)
    y = df['label'].values
    return X, y


def preprocessa(X, y):
    """
    Normalizzazione delle feature e encoding delle label.
    Restituisce X, y trasformati + gli oggetti scaler/encoder da salvare.
    """
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    # Lo scaler è dentro la Pipeline — qui lo creiamo solo per info
    print(f"   Classi trovate: {list(le.classes_)}")
    return X, y_enc, le


# ─────────────────────────────────────────
# 2. TRAINING
# ─────────────────────────────────────────

def crea_pipeline_svm():
    """
    Pipeline: StandardScaler → SVM con kernel RBF.
    Lo scaler è incluso nella pipeline così viene applicato
    automaticamente sia in training che in inferenza.
    """
    return Pipeline([
        ('scaler', StandardScaler()),
        ('clf', SVC(
            kernel='rbf',
            C=10,
            gamma='scale',
            probability=True,    # serve per predict_proba (confidence score)
            random_state=RANDOM_SEED
        ))
    ])


def crea_pipeline_mlp():
    """
    Pipeline: StandardScaler → MLP a due layer nascosti.
    Architettura leggera, pensata per inferenza real-time.
    """
    return Pipeline([
        ('scaler', StandardScaler()),
        ('clf', MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation='relu',
            max_iter=500,
            random_state=RANDOM_SEED,
            early_stopping=True,    # evita overfitting
            validation_fraction=0.1
        ))
    ])


def valuta_modello(pipeline, X_train, X_test, y_train, y_test, le, nome):
    """
    Addestra, valuta e stampa le metriche per un singolo modello.
    Restituisce l'accuracy sul test set.
    """
    print(f"\n{'='*50}")
    print(f"  Modello: {nome}")
    print(f"{'='*50}")

    # Cross-validation sul training set (5-fold)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring='accuracy')
    print(f"  Cross-val accuracy (5-fold): "
          f"{cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Training finale su tutto il train set
    pipeline.fit(X_train, y_train)

    # Valutazione sul test set
    y_pred = pipeline.predict(X_test)
    accuracy = (y_pred == y_test).mean()
    print(f"  Test accuracy: {accuracy:.3f}\n")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    return accuracy, y_pred


def salva_artefatti(pipeline, le, nome_modello, output_dir):
    """
    Salva il modello (pipeline completa) e il LabelEncoder.
    La pipeline include già lo scaler — non servono file separati.
    """
    os.makedirs(output_dir, exist_ok=True)

    model_path = os.path.join(output_dir, f'{nome_modello}.pkl')
    encoder_path = os.path.join(output_dir, 'label_encoder.pkl')

    with open(model_path, 'wb') as f:
        pickle.dump(pipeline, f)
    with open(encoder_path, 'wb') as f:
        pickle.dump(le, f)

    print(f"  💾 Modello salvato: {model_path}")
    print(f"  💾 Encoder salvato: {encoder_path}")


def salva_confusion_matrix(y_test, y_pred, le, nome_modello, output_dir):
    """Salva la confusion matrix come immagine PNG."""
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le.classes_)

    fig, ax = plt.subplots(figsize=(7, 6))
    disp.plot(ax=ax, colorbar=False, cmap='Blues')
    ax.set_title(f'Confusion Matrix — {nome_modello}')
    plt.tight_layout()

    path = os.path.join(output_dir, f'confusion_matrix_{nome_modello}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  📊 Confusion matrix salvata: {path}")


# ─────────────────────────────────────────
# 3. MAIN
# ─────────────────────────────────────────

def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ Dataset non trovato: {CSV_PATH}")
        print("   Esegui prima data_collector.py")
        return

    # 1. Carica e preprocessa
    X, y = carica_dataset(CSV_PATH)
    X, y_enc, le = preprocessa(X, y)

    # 2. Split train/test (80/20, stratificato per mantenere proporzioni)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc,
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=y_enc
    )
    print(f"   Train: {len(X_train)} campioni | Test: {len(X_test)} campioni\n")

    # 3. Definisci i modelli da confrontare
    modelli = {
        'svm':  crea_pipeline_svm(),
        'mlp':  crea_pipeline_mlp(),
    }

    risultati = {}

    for nome, pipeline in modelli.items():
        accuracy, y_pred = valuta_modello(
            pipeline, X_train, X_test, y_train, y_test, le, nome.upper()
        )
        risultati[nome] = accuracy

        salva_artefatti(pipeline, le, nome, OUTPUT_DIR)
        salva_confusion_matrix(y_test, y_pred, le, nome, OUTPUT_DIR)

    # 4. Scegli il modello migliore e salvalo come 'best_model.pkl'
    migliore_nome = max(risultati, key=risultati.get)
    migliore_pipeline = modelli[migliore_nome]

    best_path = os.path.join(OUTPUT_DIR, 'best_model.pkl')
    with open(best_path, 'wb') as f:
        pickle.dump(migliore_pipeline, f)

    print(f"\n{'='*50}")
    print(f"  🏆 Modello migliore: {migliore_nome.upper()} "
          f"(accuracy: {risultati[migliore_nome]:.3f})")
    print(f"  Salvato come: {best_path}")
    print(f"{'='*50}")

    # 5. Riepilogo finale
    print("\n📋 Riepilogo confronto:")
    for nome, acc in risultati.items():
        print(f"   {nome.upper():6s}  →  {acc:.3f}")

    print("\n✅ Training completato.")
    print(f"   Usa 'models/best_model.pkl' in gestures.py per l'inferenza.")


if __name__ == '__main__':
    main()
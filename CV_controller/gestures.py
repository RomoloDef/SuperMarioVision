import pickle
import os
import numpy as np

class GestureClassifier:
    def __init__(self, model_path=None, encoder_path=None):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = model_path or os.path.join(root_dir, 'models', 'best_model.pkl')
        self.encoder_path = encoder_path or os.path.join(root_dir, 'models', 'label_encoder.pkl')
        
        # Fallback se non trovato
        if not os.path.exists(self.model_path):
            self.model_path = 'models/best_model.pkl'
            self.encoder_path = 'models/label_encoder.pkl'
            
        self.model = None
        self.encoder = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path) and os.path.exists(self.encoder_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.encoder_path, 'rb') as f:
                    self.encoder = pickle.load(f)
                print(f"[OK] Modello caricato con successo da {self.model_path}")
            except Exception as e:
                print(f"[ERRORE] Errore nel caricamento del modello: {e}")
        else:
            print(f"[ATTENZIONE] Modello non trovato in {self.model_path}. Assicurati di aver eseguito train_classifier.py.")

    def predict_gesture(self, landmarks):
        if self.model is None or self.encoder is None:
            return "unknown", 0.0

        # Estrazione feature (x, y, z, visibility per ognuno dei 33 landmark)
        features = []
        for lm in landmarks:
            features.extend([lm.x, lm.y, lm.z, lm.visibility])
        features = np.array(features).reshape(1, -1)
        
        prediction = self.model.predict(features)[0]
        label = self.encoder.inverse_transform([prediction])[0]
        
        try:
            probabilities = self.model.predict_proba(features)[0]
            confidence = np.max(probabilities)
        except Exception:
            confidence = 1.0
            
        return label, confidence

_classifier = None

def predict_gesture(landmarks):
    global _classifier
    if _classifier is None:
        _classifier = GestureClassifier()
    return _classifier.predict_gesture(landmarks)

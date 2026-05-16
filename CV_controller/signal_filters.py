import numpy as np

class KalmanFilter:
    """
    Un filtro di Kalman molto semplificato per ridurre il jitter dei landmark.
    Si applica singolarmente a ogni coordinata (x, y, z).
    """
    def __init__(self, process_variance=1e-5, measurement_variance=1e-3):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.posteri_estimate = 0.0
        self.posteri_error_estimate = 1.0

    def update(self, measurement):
        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance

        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate

        return self.posteri_estimate

class MovingAverageFilter:
    """
    Filtro a media mobile semplice.
    """
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.history = []

    def update(self, measurement):
        self.history.append(measurement)
        if len(self.history) > self.window_size:
            self.history.pop(0)
        return sum(self.history) / len(self.history)

class PoseFilter:
    """
    Applica il filtraggio all'intero set di landmark (33 punti * 3 coordinate).
    """
    def __init__(self, filter_type='kalman', **kwargs):
        self.filter_type = filter_type
        self.filters = {} # Dizionario di filtri (una chiave per ogni coordinata di ogni landmark)

    def filter(self, landmarks):
        if not landmarks:
            return None
        
        filtered_landmarks = []
        for i, lm in enumerate(landmarks):
            # Filtriamo x, y, z
            for attr in ['x', 'y', 'z']:
                key = f"{i}_{attr}"
                if key not in self.filters:
                    if self.filter_type == 'kalman':
                        self.filters[key] = KalmanFilter()
                    else:
                        self.filters[key] = MovingAverageFilter()
                
                val = getattr(lm, attr)
                filtered_val = self.filters[key].update(val)
                setattr(lm, attr, filtered_val)
            
            filtered_landmarks.append(lm)
        
        return filtered_landmarks

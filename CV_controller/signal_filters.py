class KalmanFilter:
    """Filtro di Kalman semplificato per ridurre il jitter dei landmark."""
    def __init__(self, process_variance=1e-5, measurement_variance=1e-3):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimate = 0.0
        self.error_estimate = 1.0

    def update(self, measurement):
        priori_error = self.error_estimate + self.process_variance
        gain = priori_error / (priori_error + self.measurement_variance)
        self.estimate = self.estimate + gain * (measurement - self.estimate)
        self.error_estimate = (1 - gain) * priori_error
        return self.estimate


class PoseFilter:
    """Applica il filtro di Kalman a ciascuna coordinata (x, y, z) dei 33 landmark."""
    def __init__(self, filter_type='kalman', **kwargs):
        self.filters = {}

    def filter(self, landmarks):
        if not landmarks:
            return None
        for i, lm in enumerate(landmarks):
            for attr in ['x', 'y', 'z']:
                key = f"{i}_{attr}"
                if key not in self.filters:
                    self.filters[key] = KalmanFilter()
                val = getattr(lm, attr)
                setattr(lm, attr, self.filters[key].update(val))
        return landmarks

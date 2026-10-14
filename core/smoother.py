import math
import time


class LowPassFilter:
    """Standard 1st-order low-pass filter."""

    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.last_val = None

    def filter(self, val: float, alpha: float = None) -> float:
        if alpha is not None:
            self.alpha = alpha
        if self.last_val is None:
            self.last_val = val
            return val
        filtered = self.alpha * val + (1.0 - self.alpha) * self.last_val
        self.last_val = filtered
        return filtered

    def reset(self):
        self.last_val = None


class OneEuroFilter:
    """
    Adaptive One-Euro Filter for jitter elimination in real-time tracking.
    Reference: Géry Casiez, Nicolas Roussel, Daniel Vogel (2012)
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.x_filter = LowPassFilter()
        self.dx_filter = LowPassFilter()
        self.last_time = None

    def _alpha(self, rate: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / rate
        return 1.0 / (1.0 + tau / te)

    def filter(self, x: float, timestamp: float = None) -> float:
        if timestamp is None:
            timestamp = time.time()

        if self.last_time is None:
            self.last_time = timestamp
            return self.x_filter.filter(x, 1.0)

        dt = timestamp - self.last_time
        if dt <= 0.0:
            dt = 1e-5

        rate = 1.0 / dt

        # Estimate derivative (speed of movement)
        prev_x = self.x_filter.last_val if self.x_filter.last_val is not None else x
        dx = (x - prev_x) * rate
        edx = self.dx_filter.filter(dx, self._alpha(rate, self.d_cutoff))

        # Adaptive cutoff based on speed
        cutoff = self.min_cutoff + self.beta * abs(edx)
        filtered_x = self.x_filter.filter(x, self._alpha(rate, cutoff))

        self.last_time = timestamp
        return filtered_x

    def reset(self):
        self.x_filter.reset()
        self.dx_filter.reset()
        self.last_time = None


class Point2DSmoother:
    """Smooths (X, Y) coordinate streams independently."""

    def __init__(self, min_cutoff: float = 1.2, beta: float = 0.005):
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)

    def smooth(self, x: float, y: float, timestamp: float = None) -> tuple[float, float]:
        if timestamp is None:
            timestamp = time.time()
        sx = self.filter_x.filter(x, timestamp)
        sy = self.filter_y.filter(y, timestamp)
        return (sx, sy)

    def reset(self):
        self.filter_x.reset()
        self.filter_y.reset()

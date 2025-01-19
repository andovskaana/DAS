from .base import TechnicalIndicator

class EMAIndicator(TechnicalIndicator):
    def calculate(self, data, window=10):
        return data.ewm(span=window, adjust=False).mean().fillna(0)

from .base import TechnicalIndicator

class SMAIndicator(TechnicalIndicator):
    def calculate(self, data, window=10):
        return data.rolling(window=window).mean().fillna(0)

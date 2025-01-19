import pandas as pd
from .base import TechnicalIndicator

class RSIIndicator(TechnicalIndicator):
    def calculate(self, data, window=14):
        delta = data.diff()
        gain = delta.where(delta > 0, 0).rolling(window=window).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(0)

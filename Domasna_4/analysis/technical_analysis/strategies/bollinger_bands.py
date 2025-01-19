from .base import TechnicalIndicator

class BollingerBandsIndicator(TechnicalIndicator):
    def calculate(self, data, window=10):
        ma = data.rolling(window=window).mean()
        std = data.rolling(window=window).std()
        upper_band = ma + (2 * std)
        lower_band = ma - (2 * std)
        return ma.fillna(0), upper_band.fillna(0), lower_band.fillna(0)

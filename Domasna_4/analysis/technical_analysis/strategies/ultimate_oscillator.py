from .base import TechnicalIndicator

class UltimateOscillatorIndicator(TechnicalIndicator):
    def calculate(self, data, high, low, window1=7, window2=14, window3=28):
        buying_pressure = data - low
        true_range = high - low

        avg1 = buying_pressure.rolling(window=window1).sum() / true_range.rolling(window=window1).sum()
        avg2 = buying_pressure.rolling(window=window2).sum() / true_range.rolling(window=window2).sum()
        avg3 = buying_pressure.rolling(window=window3).sum() / true_range.rolling(window=window3).sum()

        ultimate_oscillator = 100 * ((4 * avg1) + (2 * avg2) + avg3) / 7
        return ultimate_oscillator.fillna(0)
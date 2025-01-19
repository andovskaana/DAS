from .base import TechnicalIndicator


class StochasticOscillatorIndicator(TechnicalIndicator):
    def calculate(self, data, high, low, window):
        highest_high = high.rolling(window=window).max()
        lowest_low = low.rolling(window=window).min()
        stochastic_oscillator = ((data - lowest_low) / (highest_high - lowest_low)) * 100
        return stochastic_oscillator.fillna(0)

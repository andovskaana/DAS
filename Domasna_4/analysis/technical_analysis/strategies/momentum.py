from .base import TechnicalIndicator


class MomentumIndicator(TechnicalIndicator):
    def calculate(self, data, window):
        result = ((data - data.shift(window)) / data.shift(window) * 100)
        return result.fillna(0)

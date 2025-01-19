from .base import TechnicalIndicator


class WilliamsPercentRangeIndicator(TechnicalIndicator):
    def calculate(self, data, high, low, window):
        # print(f"Received data: {data}")
        # print(f"Received high: {high}")
        # print(f"Received low: {low}")
        # print(f"Received window: {window}")

        highest_high = high.rolling(window=window).max()
        lowest_low = low.rolling(window=window).min()
        result = (-100 * (highest_high - data) / (highest_high - lowest_low)).fillna(0)
        # print(f"Calculated Williams %R: {result}")
        return result

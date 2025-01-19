from abc import ABC, abstractmethod

class TechnicalIndicator(ABC):
    @abstractmethod
    def calculate(self, data, **kwargs):
        pass
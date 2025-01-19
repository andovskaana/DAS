
class TechnicalAnalysisContext:
    def __init__(self):
        self.strategies = {}

    def add_strategy(self, name, strategy):
        self.strategies[name] = strategy

    def execute_strategy(self, name, *args, **kwargs):
        if name not in self.strategies:
            raise ValueError(f"Strategy {name} not found")

        # print(f"Executing strategy: {name}")
        # print(f"Positional args: {args}")
        # print(f"Keyword args: {kwargs}")

        return self.strategies[name].calculate(*args, **kwargs)

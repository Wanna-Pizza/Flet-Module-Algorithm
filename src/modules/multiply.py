from .base import BaseModule


class MultiplyModule(BaseModule):
    """Multiply a single numeric item by `factor` from config.

    For linear/ForEach flow this module expects a single numeric value and
    returns a single numeric value. Iteration should be done by `ForEachModule`.
    """
    def __init__(self, name: str = "Multiply", config: dict | None = None):
        super().__init__(name, config)
        self.input_type = "int|float"
        self.output_type = "int|float"
        self.input_count = 1
        self.output_count = 1

    def process(self, input_data, logger=None):
        factor = float(self.config.get("factor", 1))
        # expect a single numeric value
        try:
            out = input_data * factor
        except Exception:
            # passthrough on failure
            out = input_data
        if logger:
            logger(f"{self.name}: multiplied item -> {out}")
        return out

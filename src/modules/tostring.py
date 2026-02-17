from .base import BaseModule


class ToStringModule(BaseModule):
    """Converts a single item to its string representation."""
    def __init__(self, name: str = "ToString", config: dict | None = None):
        super().__init__(name, config)
        self.input_type = "Any"
        self.output_type = "str"
        self.input_count = 1
        self.output_count = 1

    def process(self, input_data, logger=None):
        out = str(input_data)
        if logger:
            logger(f"{self.name}: converted item to string -> {out}")
        return out

from .base import BaseModule


class IntSource(BaseModule):
    """Produces a list of integers for testing.

    Config options:
      - start: starting int (inclusive)
      - count: how many ints
    """
    def __init__(self, name: str = "IntSource", config: dict | None = None):
        super().__init__(name, config)
        # source: no input
        self.input_type = "None"
        self.input_count = 0
        # outputs a list of ints
        self.output_type = "list[int]"
        self.output_count = 1

    def process(self, input_data, logger=None):
        start = int(self.config.get("start", 1))
        count = int(self.config.get("count", 5))
        lst = [start + i for i in range(count)]
        if logger:
            logger(f"{self.name}: produced {len(lst)} ints")
        return lst

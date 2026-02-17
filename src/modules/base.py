from typing import Callable


class BaseModule:
    """Minimal module interface for list-stream pipeline.

    `process(self, input_data: list | Any, logger: Callable[[str], None] | None)`
    should accept the accumulated payload (often a list) and return a list.
    """
    def __init__(self, name: str, config: dict | None = None):
        self.name = name
        self.config = config or {}
        # compatibility metadata used by the UI
        self.input_type = "Any"
        self.output_type = "Any"
        self.input_count = 1
        self.input_types = [self.input_type]
        self.output_count = 1
        self.output_types = [self.output_type]
        # runtime state
        self.last_input = None
        self.last_output = None
        self.propagated_output = None

    def process(self, input_data, logger: Callable[[str], None] | None = None):
        raise NotImplementedError()

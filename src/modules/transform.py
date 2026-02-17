from .base import BaseModule


class TransformModule(BaseModule):
    """Apply a transformation expression to each item (map-like).

    Config:
      - expr: Python expression evaluated with `x` bound to the item (e.g. "x*2" or "x['v']*1.1")
      - field: optional — if set and item is dict, update that field instead of replacing whole item
    """
    def __init__(self, name: str = "Transform", config: dict | None = None):
        super().__init__(name, config)
        self.input_type = "list"
        self.output_type = "list"
        self.input_count = 1
        self.output_count = 1

    def _eval(self, x, expr: str):
        if not expr:
            return x
        try:
            # restrict builtins for safety; only `x` is available in globals
            return eval(expr, {"__builtins__": None}, {"x": x})
        except Exception:
            # on error, return original value to avoid breaking pipelines
            return x

    def _apply_one(self, itm, expr: str, field: str | None):
        if field and isinstance(itm, dict):
            val = itm.get(field)
            new = self._eval(val, expr)
            out = dict(itm)
            out[field] = new
            return out
        else:
            return self._eval(itm, expr)

    def process(self, input_data, logger=None):
        expr = (self.config or {}).get("expr", "")
        field = (self.config or {}).get("field")

        if input_data is None:
            return []

        if isinstance(input_data, list):
            out = [self._apply_one(i, expr, field) for i in input_data]
        else:
            out = self._apply_one(input_data, expr, field)

        if logger:
            try:
                logger(f"{self.name}: transformed -> {len(out) if isinstance(out, list) else 1} items")
            except Exception:
                pass
        return out

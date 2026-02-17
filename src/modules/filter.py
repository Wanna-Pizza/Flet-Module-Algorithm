from .base import BaseModule


class FilterModule(BaseModule):
    """Filter a list using a boolean expression.

    Config options:
      - expr: Python expression evaluated with `x` bound to each item (e.g. "x % 2 == 0")
      - mode: "keep" (default) or "drop" — whether predicate keeps or drops matching items
      - field: optional key to extract from dict items before evaluating expression
    """
    def __init__(self, name: str = "Filter", config: dict | None = None):
        super().__init__(name, config)
        self.input_type = "list"
        self.output_type = "list"
        self.input_count = 1
        self.output_count = 1

    def _eval_pred(self, x, expr: str):
        if not expr:
            return True
        # safe-ish eval: no builtins, only `x` available
        try:
            return bool(eval(expr, {"__builtins__": None}, {"x": x}))
        except Exception:
            # on any evaluation error, treat as False
            return False

    def process(self, input_data, logger=None):
        expr = (self.config or {}).get("expr") or ""
        mode = (self.config or {}).get("mode") or "keep"
        field = (self.config or {}).get("field")

        if input_data is None:
            return []

        if not isinstance(input_data, list):
            try:
                items = list(input_data)
            except Exception:
                items = [input_data]
        else:
            items = input_data

        out = []
        for itm in items:
            val = itm
            if field and isinstance(itm, dict):
                val = itm.get(field)
            keep = self._eval_pred(val, expr)
            if mode == "keep" and keep:
                out.append(itm)
            elif mode == "drop" and not keep:
                out.append(itm)

        if logger:
            logger(f"{self.name}: filtered {len(items)} -> {len(out)} items (expr={expr!r}, mode={mode})")
        return out

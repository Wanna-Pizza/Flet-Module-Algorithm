from typing import List
import asyncio
import inspect

from .base import BaseModule


class ForEachModule(BaseModule):
    """Iterates over input list and runs a body of modules for each item.

    `body` should be a list where each element is one of:
      - a `BaseModule` *instance* (it will be re-instantiated per-item using its class and config),
      - a module *class* (callable) which will be instantiated with its default args,
      - a tuple `(ModuleClass, config_dict)` which will be instantiated as `ModuleClass(config=config_dict)`,
      - a callable factory that returns a `BaseModule` instance when called with no args.

    For each item in the input list the module will create fresh instances for the
    body steps and pass the single item through them sequentially. The final
    outputs for each item are collected into the returned list.
    """
    def __init__(self, name: str = "ForEach", body: List | None = None, config: dict | None = None):
        super().__init__(name, config)
        self.body = body or []
        # preview state for UI: stores last input/output observed for each body step
        # (updated during `process` so nested views can show the last-item example)
        self._body_preview = []
    
    def add_body_module(self, module_type: type, config: dict = None):
        """Add a module to the body using standardized (Class, config) format."""
        self.body.append((module_type, config))
    
    def remove_body_module(self, index: int):
        """Remove a module from the body by index."""
        if 0 <= index < len(self.body):
            self.body.pop(index)
    
    def reorder_body_modules(self, old_index: int, new_index: int):
        """Reorder modules in the body."""
        if 0 <= old_index < len(self.body) and 0 <= new_index < len(self.body):
            item = self.body.pop(old_index)
            self.body.insert(new_index, item)

    def _instantiate_step(self, spec):
        """Return a fresh BaseModule instance from a body spec."""
        # already an instance -> create a new one from its class and config
        try:
            from .base import BaseModule as _BM
        except Exception:
            _BM = None

        if _BM is not None and isinstance(spec, _BM):
            cls = spec.__class__
            # Try to preserve instance attributes that match constructor params
            try:
                sig = inspect.signature(cls.__init__)
                params = [p.name for p in list(sig.parameters.values())[1:]]
                kwargs = {name: getattr(spec, name) for name in params if hasattr(spec, name)}
                if kwargs:
                    return cls(**kwargs)
            except Exception:
                pass
            # Fallback to using `config` attribute if present
            cfg = getattr(spec, "config", None)
            try:
                return cls(config=cfg)
            except TypeError:
                return cls()

        # tuple (Class, config)
        if isinstance(spec, tuple) and len(spec) == 2 and isinstance(spec[0], type):
            cls, cfg = spec
            # If cfg is a dict, try to pass matching kwargs (e.g. body=...)
            if isinstance(cfg, dict):
                kwargs = {k: v for k, v in cfg.items() if k in inspect.signature(cls.__init__).parameters}
                if kwargs:
                    try:
                        return cls(**kwargs)
                    except Exception:
                        pass
                # fall through to attempt passing full dict via `config` if ctor supports it
            try:
                return cls(config=cfg)
            except TypeError:
                try:
                    return cls(cfg)
                except Exception:
                    return cls()

        # callable: could be a class or factory
        if callable(spec):
            try:
                inst = spec()
                return inst
            except TypeError:
                # couldn't call without args
                raise

        raise TypeError(f"Unsupported body spec for ForEach: {spec}")

    def process(self, input_data, logger=None):
        if not isinstance(input_data, list):
            items = [input_data]
        else:
            items = input_data

        # reset preview info for body steps — will contain last-item example after run
        self._body_preview = [None] * len(self.body)

        out = []
        for itm in items:
            current = itm
            for idx, spec in enumerate(self.body):
                # create a fresh module instance for this step
                try:
                    mod = self._instantiate_step(spec)
                except Exception:
                    # if instantiation fails, try to use spec directly (best-effort)
                    mod = spec

                # prepare preview entry (mark step as running)
                try:
                    step_name = getattr(mod, "name", None) or (spec[0].__name__ if isinstance(spec, tuple) else getattr(spec, "__name__", str(spec)))
                    self._body_preview[idx] = {"name": step_name, "last_input": current, "last_output": None, "status": "running"}
                except Exception:
                    pass

                try:
                    prev = current
                    current = mod.process(current, logger=logger)
                except Exception:
                    # fallback to async if module is coroutine
                    try:
                        if asyncio.iscoroutinefunction(mod.process):
                            current = asyncio.run(mod.process(current, logger=logger))
                        else:
                            pass
                    except Exception:
                        pass

                # update preview for this body step (shows last processed item's input/output)
                try:
                    # include nested preview for ForEach sub-steps (so UI can render nested previews)
                    nested = getattr(mod, "_body_preview", None)
                    entry = {"name": step_name, "last_input": prev, "last_output": current, "status": "done"}
                    if nested is not None:
                        # copy nested preview structure into the parent's preview entry
                        entry["nested_preview"] = nested
                    self._body_preview[idx] = entry
                except Exception:
                    pass

            out.append(current)

        if logger:
            logger(f"{self.name}: iterated {len(items)} items -> produced {len(out)} items")
        return out

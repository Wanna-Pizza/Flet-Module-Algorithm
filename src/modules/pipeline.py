from typing import Callable, Any, List
import inspect
import asyncio

from .base import BaseModule


class Pipeline:
    """Simple linear pipeline that passes a payload (usually a list) through modules.

    Each module receives the full accumulated payload and returns the next payload.
    """
    def __init__(self, modules: List[BaseModule] | None = None):
        self.modules = modules or []

    def add(self, module: BaseModule) -> None:
        self.modules.append(module)

    async def run(self, initial_input: Any = None, logger: Callable[[str], None] | None = None, on_module_output: Callable[[BaseModule, Any], None] | None = None) -> Any:
        data = initial_input if initial_input is not None else []
        if logger:
            logger("Pipeline: starting")
        for m in self.modules:
            if logger:
                logger(f"Pipeline: running module '{m.name}'")
            pre = data
            try:
                m.last_input = pre
            except Exception:
                m.last_input = None

            try:
                if inspect.iscoroutinefunction(m.process):
                    result = await m.process(data, logger=logger)
                else:
                    result = await asyncio.to_thread(m.process, data, logger)
            except Exception as exc:
                if logger:
                    logger(f"Pipeline: module '{m.name}' failed: {exc}")
                raise

            m.last_output = result
            data = result
            try:
                m.propagated_output = data
            except Exception:
                m.propagated_output = None

            if on_module_output:
                try:
                    on_module_output(m, m.last_output)
                except Exception as exc:
                    if logger:
                        try:
                            import traceback
                            tb = traceback.format_exc()
                            logger(f"Pipeline: on_module_output callback failed for '{m.name}': {exc}\n{tb}")
                        except Exception:
                            logger(f"Pipeline: on_module_output callback failed for '{m.name}': {exc}")
        if logger:
            logger("Pipeline: finished")
        return data

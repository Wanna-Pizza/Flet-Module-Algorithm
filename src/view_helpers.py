"""Helper utilities for PipelineModuleView."""

import json
import inspect
import flet as ft
from typing import Any, List, Tuple, Optional


# Module registry for dynamic instantiation
MODULE_REGISTRY = {}

# Registry of PipelineModuleView instances (keyed by id(view) string) to
# facilitate cross-level drag/drop (move view between top-level and ForEach).
VIEW_REGISTRY = {}


def register_modules():
    """Lazy registration of modules to avoid circular imports."""
    global MODULE_REGISTRY
    if not MODULE_REGISTRY:
        from modules import IntSource, MultiplyModule, ToStringModule, ForEachModule
        MODULE_REGISTRY = {
            "IntSource": IntSource,
            "MultiplyModule": MultiplyModule,
            "ToStringModule": ToStringModule,
            "ForEachModule": ForEachModule,
        }
    return MODULE_REGISTRY


def register_view(view):
    """Register a PipelineModuleView instance for global lookup by id."""
    try:
        VIEW_REGISTRY[str(id(view))] = view
    except Exception:
        pass


def unregister_view(view):
    """Unregister a view instance from the global registry."""
    try:
        VIEW_REGISTRY.pop(str(id(view)), None)
    except Exception:
        pass


def get_view_by_id(id_str: str):
    """Lookup a previously-registered view by its id string."""
    return VIEW_REGISTRY.get(str(id_str))


def get_module_class(name: str):
    """Get module class by name."""
    return register_modules().get(name)


def safe_json_serialize(value: Any, indent: int = 2) -> str:
    """Safely serialize value to JSON string."""
    if value is None:
        return ""
    try:
        if isinstance(value, (dict, list, tuple, str, int, float, bool, type(None))):
            return json.dumps(value, indent=indent)
        return str(value)
    except Exception:
        return str(value)


def safe_update(control):
    """Safely update a control only if it's attached to a page."""
    if control and (getattr(control, 'page', None) is not None):
        control.update()


def extract_module_from_spec(spec) -> Optional[Any]:
    """Extract or create module instance from body spec.
    
    Supports:
    - Module instance -> return as-is
    - (Class, config) tuple -> instantiate with config
    - Class -> instantiate with no args
    """
    from modules.base import BaseModule
    
    # Check if it's already a module instance
    if isinstance(spec, BaseModule):
        return spec
    
    # Check if it's a tuple (Class, config)
    if isinstance(spec, tuple) and len(spec) == 2:
        cls, config = spec
        if isinstance(cls, type):
            return _instantiate_module(cls, config)
    
    # Check if it's a class
    if isinstance(spec, type):
        return spec()
    
    return None


def _instantiate_module(cls, config):
    """Instantiate module class with flexible config handling.

    - If `config` is a dict, pass keys that match the constructor parameters as
      keyword arguments (useful for modules like ForEachModule(body=...)).
    - Fallbacks: cls(config=...), cls(config) or cls() to preserve backwards
      compatibility with existing module constructors.
    """
    sig = inspect.signature(cls.__init__)
    params = [p.name for p in list(sig.parameters.values())[1:]]  # skip self

    # If config is a mapping, prefer passing matching named parameters
    if isinstance(config, dict):
        kwargs = {k: v for k, v in config.items() if k in params}
        if kwargs:
            try:
                return cls(**kwargs)
            except Exception:
                pass
        # no matching named params — fall through so we can try `config=` or legacy forms

    # Legacy handling for modules that expect a single `config` argument
    if 'config' in params:
        return cls(config=config) if config else cls()

    if len(params) == 0:
        return cls()

    if len(params) == 1:
        return cls(config) if config else cls()

    # Best-effort fallback
    try:
        return cls()
    except Exception:
        return None


def get_input_data(module, parent_view, self_in_parent_views) -> Tuple[Any, Any]:
    """Get input data considering parent preview.

    Returns:
        (inp, full_inp): Input value and full accumulated input
    """
    # Only attempt to use parent's _body_preview if this view is already
    # registered in the parent's `body_views` list (avoids index errors
    # during child construction).
    if (
        parent_view
        and hasattr(parent_view.module, "_body_preview")
        and self_in_parent_views
        and getattr(parent_view, "body_views", None)
        and self_in_parent_views in parent_view.body_views
    ):
        idx = parent_view.body_views.index(self_in_parent_views)
        preview = parent_view.module._body_preview
        if idx < len(preview) and preview[idx] is not None:
            return preview[idx].get("last_input"), None

    inp = getattr(module, "last_input", None) or getattr(module, "_raw_last_input", None)
    full_inp = getattr(module, "accumulated_input", None)
    return inp, full_inp


def get_propagated_data(module, parent_view, self_in_parent_views) -> Any:
    """Get propagated output considering parent preview."""
    if (
        parent_view
        and hasattr(parent_view.module, "_body_preview")
        and self_in_parent_views
        and getattr(parent_view, "body_views", None)
        and self_in_parent_views in parent_view.body_views
    ):
        idx = parent_view.body_views.index(self_in_parent_views)
        preview = getattr(parent_view.module, "_body_preview", [])
        if idx < len(preview) and preview[idx] is not None:
            return preview[idx].get("last_output")

    return getattr(module, "propagated_output", None)


def calculate_output_diff(prop: Any, inp: Any) -> Tuple[List[str], List[str]]:
    """Calculate added and changed keys between propagated output and input.
    
    Returns:
        (added_keys, changed_keys)
    """
    added_keys = []
    changed_keys = []
    
    if isinstance(prop, dict) and isinstance(inp, dict):
        for k, v in prop.items():
            if k not in inp:
                added_keys.append(k)
            elif inp.get(k) != v:
                changed_keys.append(k)
    
    return added_keys, changed_keys


def build_diff_spans(added_keys: List[str], changed_keys: List[str]) -> List[ft.TextSpan]:
    """Build text spans showing added and changed keys."""
    spans = [ft.TextSpan("Propagated output:")]
    
    if added_keys:
        spans.append(ft.TextSpan("  Added: "))
        for i, k in enumerate(added_keys):
            if i:
                spans.append(ft.TextSpan(", "))
            spans.append(ft.TextSpan(k, style=ft.TextStyle(color="green")))
    
    if changed_keys:
        spans.append(ft.TextSpan("  Changed: "))
        for i, k in enumerate(changed_keys):
            if i:
                spans.append(ft.TextSpan(", "))
            spans.append(ft.TextSpan(k, style=ft.TextStyle(color="orange")))
    
    return spans


def persist_config_to_parent_body(view_instance, parent_view):
    """Persist config changes back to parent ForEach body spec."""
    if not parent_view or parent_view.module.__class__.__name__ != 'ForEachModule':
        return
    
    if view_instance not in parent_view.body_views:
        return
    
    idx = parent_view.body_views.index(view_instance)
    spec = parent_view.module.body[idx]
    config_copy = dict(view_instance.module.config or {})
    
    from modules.base import BaseModule
    
    match spec:
        case (type() as cls, _):
            parent_view.module.body[idx] = (cls, config_copy)
        case BaseModule():
            parent_view.module.body[idx] = (spec.__class__, config_copy)
        case _:
            parent_view.module.body[idx] = (view_instance.module.__class__, config_copy)


# Config schema definitions for well-known modules
CONFIG_SCHEMAS = {
    'MultiplyModule': [('factor', float, 1.0)],
    'IntSource': [('start', int, 1), ('count', int, 5)],
}


def get_config_fields(module) -> List[Tuple[str, type, Any]]:
    """Get config fields for a module with type and default value.
    
    Returns:
        List of (name, type, value) tuples
    """
    cls_name = module.__class__.__name__
    fields = []
    
    # Add schema fields
    if cls_name in CONFIG_SCHEMAS:
        for name, typ, default in CONFIG_SCHEMAS[cls_name]:
            val = module.config.get(name, default)
            fields.append((name, typ, val))
    
    # Add any extra config keys not in schema
    for k, v in (module.config or {}).items():
        if not any(f[0] == k for f in fields):
            fields.append((k, type(v), v))
    
    return fields

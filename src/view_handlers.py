"""Event handlers for PipelineModuleView."""

import json
import flet as ft
from typing import Optional
from view_helpers import get_module_class, persist_config_to_parent_body, safe_update, extract_module_name_from_drag_event


class DragDropHandler:
    """Handles drag and drop operations for module body."""
    
    def __init__(self, view_instance):
        self.view = view_instance
    
    def on_will_accept_module(self, e) -> bool:
        """Preview the dragged module's visual style on the drop zone."""
        if not (hasattr(e, 'src_id') and e.src_id and hasattr(e, 'page')):
            return True
        
        src_ctrl = e.page.get_control(e.src_id)
        if not (src_ctrl and hasattr(src_ctrl, 'content') and hasattr(e, 'control') and hasattr(e.control, 'content')):
            return True
        
        src_bg = getattr(src_ctrl.content, 'bgcolor', None)
        if src_bg:
            e.control.content.bgcolor = src_bg
        e.control.content.border = None
        e.control.update()
        return True
    
    def on_drag_leave(self, e):
        """Reset drop zone appearance when drag leaves."""
        e.control.content.bgcolor = 'white,0.02'
        e.control.content.border = ft.border.all(1, 'white,0.1')
        e.control.update()
    
    def on_accept_new_module(self, e):
        """Handle dropping a new module from palette into ForEach body."""
        module_name = self._extract_module_name(e)
        
        if not module_name:
            return
        
        module_cls = get_module_class(module_name)
        if not module_cls:
            return
        
        # Add module to body and refresh views
        self.view.module.body.append((module_cls, None))
        self.view._create_body_views()
        
        if hasattr(self.view, "_body_views_column"):
            self.view._body_views_column.controls = self.view.body_views
            safe_update(self.view._body_views_column)
        
        safe_update(self.view)
    
    def _extract_module_name(self, e) -> Optional[str]:
        """Extract module name from drag event using helper in view_helpers."""
        try:
            nm = extract_module_name_from_drag_event(e)
            if nm:
                return nm
        except Exception:
            pass
        return None


class ConfigHandler:
    """Handles configuration changes."""
    
    def __init__(self, view_instance):
        self.view = view_instance
        self.module = view_instance.module
    
    def on_inline_bool_change(self, key: str, val: bool):
        """Handle inline boolean config change."""
        self.module.config[key] = bool(val)
        self._apply_config_change()
    
    def on_inline_number_change(self, key: str, raw: str, typ: type):
        """Handle inline number config change with validation."""
        raw = (raw or '').strip()
        try:
            val = typ(raw)
        except Exception:
            return  # Allow user to continue typing
        
        self.module.config[key] = val
        self._apply_config_change()
    
    def on_inline_text_change(self, key: str, raw: str):
        """Handle inline text config change."""
        self.module.config[key] = raw
        self._apply_config_change()
    
    def _apply_config_change(self):
        """Apply config change and update views."""
        persist_config_to_parent_body(self.view, self.view.parent_view)
        
        # Update JSON preview
        if hasattr(self.view, 'config_field') and self.view.config_field:
            self.view.config_field.value = json.dumps(self.module.config, indent=2)
            safe_update(self.view.config_field)
        
        # Refresh preview displays
        self.view.refresh_preview()
        safe_update(self.view)
    



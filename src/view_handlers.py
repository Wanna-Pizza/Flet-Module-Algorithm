"""Event handlers for PipelineModuleView."""

import json
import flet as ft
from typing import Optional
from view_helpers import get_module_class, persist_config_to_parent_body, safe_update


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
        """Extract module name from drag event."""
        # Try to get from src_id control
        if hasattr(e, 'src_id') and e.src_id and hasattr(e, 'page'):
            src_ctrl = e.page.get_control(e.src_id)
            if src_ctrl and hasattr(src_ctrl, 'data') and isinstance(src_ctrl.data, str):
                return src_ctrl.data
        
        # Try to get from event data
        if hasattr(e, 'data') and isinstance(e.data, str):
            from view_helpers import register_modules
            if e.data in register_modules():
                return e.data
        
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
    
    def show_config_dialog(self, e):
        """Open JSON editor dialog for module config."""
        cfg_text = json.dumps(self.module.config, indent=2) if self.module.config else "{}"
        editor = ft.TextField(value=cfg_text, multiline=True, expand=True)
        err = ft.Text("", size=12, color="red")
        
        dlg = ft.AlertDialog(
            title=ft.Text(f"{self.module.name} config"),
            content=ft.Container(
                content=ft.Column([editor, err]),
                width=600,
                height=320
            )
        )
        
        def close(ev=None):
            dlg.open = False
            self.view.page.update()
        
        def save(ev):
            text = editor.value.strip()
            
            # Parse JSON
            if not text:
                new_cfg = {}
            else:
                try:
                    new_cfg = json.loads(text)
                except Exception as exc:
                    err.value = f"Invalid JSON: {exc}"
                    self.view.page.update()
                    return
            
            # Apply config
            self.module.config = new_cfg
            persist_config_to_parent_body(self.view, self.view.parent_view)
            
            # Update config field
            if hasattr(self.view, 'config_field') and self.view.config_field:
                self.view.config_field.value = json.dumps(new_cfg, indent=2) if new_cfg else ""
                safe_update(self.view.config_field)
            
            # Rebuild inline controls
            self.view._build_inline_config_controls()
            
            close()
        
        dlg.actions = [
            ft.ElevatedButton("Save", on_click=save),
            ft.ElevatedButton("Cancel", on_click=close)
        ]
        
        self.view.page.dialog = dlg
        dlg.open = True
        self.view.page.update()


class DialogHandler:
    """Handles dialog displays."""
    
    def __init__(self, view_instance):
        self.view = view_instance
        self.module = view_instance.module
    
    def show_output_dialog(self, e):
        """Show module output in a dialog."""
        last_output = getattr(self.module, "last_output", None)
        
        if last_output is None:
            body = ft.Text("No output")
        else:
            from view_helpers import safe_json_serialize
            txt = safe_json_serialize(last_output)
            body = ft.TextField(value=txt, multiline=True, expand=True, disabled=True)
        
        dlg = ft.AlertDialog(
            title=ft.Text(f"{self.module.name} output"),
            content=ft.Container(content=body, width=600, height=300)
        )
        
        def close_dlg(ev):
            dlg.open = False
            self.view.page.update()
        
        dlg.actions = [ft.ElevatedButton("Close", on_click=close_dlg)]
        
        self.view.page.dialog = dlg
        dlg.open = True
        self.view.page.update()

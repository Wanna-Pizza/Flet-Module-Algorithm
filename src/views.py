"""Pipeline module view with optimal structure and minimal duplication."""

import flet as ft
from typing import Callable, Optional

from view_helpers import (
    extract_module_from_spec, safe_update, get_module_class,
    safe_json_serialize, register_view, unregister_view,
)
from view_builders import ViewComponentBuilder
from view_handlers import ConfigHandler, DialogHandler


class PipelineModuleView(ft.Container):
    def __init__(self, module, on_delete_callback: Callable = None, nesting_level: int = 0, parent_view=None):
        super().__init__()
        self.module = module
        self.on_delete_callback = on_delete_callback
        self.nesting_level = nesting_level
        self.parent_view = parent_view
        
        # UI state
        self._collapsed = False
        self.show_input = True
        self.show_propagated = True
        self._mounted = False
        
        # UI components
        self.status = ft.Text("idle", size=12, color="grey")
        self.config_field: Optional[ft.TextField] = None
        self.last_input_display: Optional[ft.TextField] = None
        self.propagated_field: Optional[ft.TextField] = None
        
        # Container styling
        self.bgcolor = 'white,0.03'
        self.border_radius = 10
        self.border = ft.border.all(1, 'white,0.2')
        
        # ForEach body views
        self.body_views = []
        
        # Handlers
        self._config_handler = ConfigHandler(self)
        self._dialog_handler = DialogHandler(self)
        
        # Register view for cross-level drag/drop lookups
        register_view(self)

        # Initialize body views if ForEach module
        from modules import ForEachModule
        if isinstance(module, ForEachModule):
            self._create_body_views()

        # Build initial content
        self.content = self._content()
    
    def set_status(self, text: str, color: Optional[str] = None):
        """Update status control safely."""
        self.status.value = text
        if color:
            self.status.color = color
        safe_update(self.status)
    
    def toggle_collapse(self, e=None):
        """Toggle expanded/collapsed state without rebuilding content."""
        self._collapsed = not self._collapsed
        
        if hasattr(self, 'collapse_btn'):
            self.collapse_btn.icon = ft.Icons.EXPAND if self._collapsed else ft.Icons.EXPAND_LESS
            safe_update(self.collapse_btn)
        
        # show/hide details
        if hasattr(self, '_details_container'):
            self._details_container.visible = not self._collapsed
            safe_update(self._details_container)

        # update parent container controls (reordering removed)
        try:
            if getattr(self, 'parent_view', None) is not None and hasattr(self.parent_view, '_body_views_column'):
                try:
                    self.parent_view._body_views_column.controls = self.parent_view._body_controls_wrapped()
                    safe_update(self.parent_view._body_views_column)
                except Exception:
                    pass
            else:
                # top-level: trigger a page update so parent (Main) can refresh module listing
                try:
                    if getattr(self, 'page', None):
                        self.page.update()
                except Exception:
                    pass
        except Exception:
            pass

        safe_update(self)
    
    def _create_body_views(self):
        """Create PipelineModuleView instances for ForEach body modules."""
        from modules import ForEachModule
        if not isinstance(self.module, ForEachModule):
            return

        self.body_views = []
        for body_spec in self.module.body:
            module_instance = extract_module_from_spec(body_spec)
            if module_instance:
                body_view = PipelineModuleView(
                    module_instance,
                    on_delete_callback=self._on_body_module_delete,
                    nesting_level=self.nesting_level + 1,
                    parent_view=self
                )
                self.body_views.append(body_view)

    def _body_controls_wrapped(self):
        """Return raw body view controls (reordering removed)."""
        return [v for v in self.body_views]



    def _on_accept_body_drop(self, e, insert_idx: int):
        """Handle drops into this ForEach body (palette add or reorder child view).

        Supports:
        - palette adds (data == module name string)
        - moving an existing body view within the same ForEach
        - moving a top-level/module-from-other-parent into this ForEach (cross-level)
        """
        # extract data (palette sends module name strings; draggables send id(view))
        data = getattr(e, 'data', None)
        if not data and getattr(e, 'src_id', None):
            src_ctrl = self.page.get_control(e.src_id)
            data = getattr(src_ctrl, 'data', None)

        # add new module from palette (string module name)
        try:
            from view_helpers import get_module_class, get_view_by_id
            if isinstance(data, str):
                # palette add (module name)
                module_cls = get_module_class(data)
                if module_cls is not None:
                    self.module.body.insert(insert_idx, (module_cls, None))
                    self._create_body_views()
                    if hasattr(self, '_body_views_column'):
                        self._body_views_column.controls = self._body_controls_wrapped()
                        safe_update(self._body_views_column)
                    return
        except Exception:
            pass

        # move existing view (data is numeric id string)
        try:
            src_id = int(data)
        except Exception:
            src_id = None

        if src_id is not None:
            # 1) moving within same ForEach
            src_idx = next((i for i, v in enumerate(self.body_views) if id(v) == src_id), None)
            if src_idx is not None:
                view = self.body_views.pop(src_idx)
                spec = self.module.body.pop(src_idx)
                insert_pos = insert_idx - 1 if src_idx < insert_idx else insert_idx
                self.module.body.insert(insert_pos, spec)
                self.body_views.insert(insert_pos, view)
                if hasattr(self, '_body_views_column'):
                    self._body_views_column.controls = self._body_controls_wrapped()
                    safe_update(self._body_views_column)
                return

            # 2) moving a top-level or other-parent view into this ForEach
            try:
                src_view = get_view_by_id(str(src_id))
                if src_view is not None:
                    # detach src_view from its parent (try to locate it in page's module lists)
                    # Best-effort: if src_view exists in a top-level modules list (Main.module_views), remove it
                    try:
                        # find Main by walking page.controls (heuristic)
                        for c in getattr(self.page, 'controls', []) or []:
                            # look for a top-level container that holds module views and detach the source view
                            try:
                                if src_view in getattr(c, 'controls', []):
                                    src_idx = c.controls.index(src_view)
                                    c.controls.pop(src_idx)
                                    # also update pipeline/modules if possible
                                    # best-effort: detach src_view from any parent container (no Main import required)
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # finally, insert into this body (use view's module class + config)
                    try:
                        parent_spec = (src_view.module.__class__, dict(getattr(src_view.module, 'config', {}) or {}))
                        self.module.body.insert(insert_idx, parent_spec)
                        self._create_body_views()
                        if hasattr(self, '_body_views_column'):
                            self._body_views_column.controls = self._body_controls_wrapped()
                            safe_update(self._body_views_column)
                        return
                    except Exception:
                        pass
            except Exception:
                # outer try (get_view_by_id / detach) failed — ignore
                pass
        # nothing handled
        return
    
    def _on_body_module_delete(self, view):
        """Handle deletion of a body module."""
        if view in self.body_views:
            idx = self.body_views.index(view)
            # unregister and remove
            try:
                unregister_view(view)
            except Exception:
                pass
            self.body_views.pop(idx)
            self.module.body.pop(idx)
            if hasattr(self, '_body_views_column'):
                try:
                    self._body_views_column.controls = self._body_controls_wrapped()
                except Exception:
                    self._body_views_column.controls = self._body_controls_wrapped()
                safe_update(self._body_views_column)
    
    def _add_module_by_name(self, name: str):
        """Programmatically add a module to ForEach body."""
        module_cls = get_module_class(name)
        if not module_cls:
            return

        self.module.body.append((module_cls, None))
        self._create_body_views()
        if hasattr(self, '_body_views_column'):
            try:
                # ensure body views container knows current controls
                self._body_views_column.controls = self._body_controls_wrapped()
            except Exception:
                self._body_views_column.controls = self._body_controls_wrapped()
            safe_update(self._body_views_column)
        self._build_inline_config_controls()
    
    def did_mount(self):
        """Called when component is mounted."""
        self._mounted = True
        if not hasattr(self, '_config_controls_container'):
            self._config_controls_container = ft.Row([], spacing=8)
        self._build_inline_config_controls()
        # if a body views container was created, ensure its controls are current
        try:
            if hasattr(self, '_body_views_column') and getattr(self, '_body_views_column', None) is not None:
                try:
                    self._body_views_column.controls = self._body_controls_wrapped()
                    safe_update(self._body_views_column)
                except Exception:
                    pass
        except Exception:
            pass

        # reordering removed — no wrapper conversion needed after mount

        return super().did_mount()
    
    def _content(self):
        """Build main content using component builder."""
        builder = ViewComponentBuilder(self)
        
        # Collapse button
        if not hasattr(self, 'collapse_btn'):
            icon = ft.Icons.EXPAND if self._collapsed else ft.Icons.EXPAND_LESS
            self.collapse_btn = ft.IconButton(icon, icon_size=15, on_click=self.toggle_collapse)
        else:
            self.collapse_btn.icon = ft.Icons.EXPAND if self._collapsed else ft.Icons.EXPAND_LESS
        
        # Action buttons
        output_btn = ft.IconButton(ft.Icons.PREVIEW, icon_size=15, on_click=self._dialog_handler.show_output_dialog)
        self.config_btn = ft.IconButton(ft.Icons.SETTINGS, icon_size=15, on_click=self._config_handler.show_config_dialog)
        
        # Delete button for body modules
        delete_btn = None
        if self.on_delete_callback:
            delete_btn = ft.IconButton(
                ft.Icons.CLOSE, icon_size=15,
                on_click=lambda e: self.on_delete_callback(self),
                tooltip="Remove from body"
            )
        
        # Build header
        header_row = builder.build_header_row(self.collapse_btn, output_btn, self.config_btn, delete_btn)
        label = ft.Container(
            content=header_row,
            alignment=ft.alignment.center_left,
            height=30,
            bgcolor='white,0.1',
            on_click=self.toggle_collapse,
        )
        
        # Build content sections
        types_row = builder.build_types_row()
        
        # Config display
        if not hasattr(self, 'config_field') or self.config_field is None:
            cfg_val = safe_json_serialize(self.module.config)
            self.config_field = ft.TextField(value=cfg_val, multiline=False, expand=True, disabled=True, text_size=12)
        
        config_row = builder.build_config_row(self.config_field, self._config_handler.show_config_dialog)
        
        # Inline config controls
        if not hasattr(self, '_config_controls_container'):
            self._config_controls_container = ft.Row([], spacing=8)
        self._build_inline_config_controls()
        
        content_container = ft.Column([types_row, config_row, self._config_controls_container], spacing=6)
        
        # ForEach body container
        body_container = None
        from modules import ForEachModule
        if isinstance(self.module, ForEachModule):
            body_container = builder.build_foreach_body_container(self.body_views, self._add_module_by_name)
            # ensure body views container knows current controls when mounted
            if hasattr(self, '_body_views_column') and getattr(self, '_mounted', False):
                try:
                    self._body_views_column.controls = self._body_controls_wrapped()
                    safe_update(self._body_views_column)
                except Exception:
                    pass
        
        # Input/output displays
        if not hasattr(self, '_input_display_container'):
            self._input_display_container = ft.Container()
        self._input_display_container.content = builder.build_input_display(self.show_input, self.toggle_input).content
        
        if not hasattr(self, '_propagated_display_container'):
            self._propagated_display_container = ft.Container()
        self._propagated_display_container.content = builder.build_propagated_display(self.show_propagated, self.toggle_propagated).content
        
        # Build details container
        if not hasattr(self, '_details_container'):
            children = [ft.Container(content_container, padding=10)]
            
            if body_container:
                self._body_container_wrapper = ft.Container(body_container, padding=ft.padding.only(left=10, right=10, bottom=10))
                children.append(self._body_container_wrapper)
            
            children.append(ft.Container(self._input_display_container, padding=6))
            children.append(ft.Container(self._propagated_display_container, padding=6))
            
            self._details_container = ft.Column(children, spacing=6)
        else:
            # Update existing details
            self._details_container.controls[0] = ft.Container(content_container, padding=10)
            
            if body_container:
                if not hasattr(self, '_body_container_wrapper'):
                    self._body_container_wrapper = ft.Container(body_container, padding=ft.padding.only(left=10, right=10, bottom=10))
                else:
                    self._body_container_wrapper.content = body_container
                
                if len(self._details_container.controls) >= 2:
                    self._details_container.controls[1] = self._body_container_wrapper
                else:
                    self._details_container.controls.insert(1, self._body_container_wrapper)
        
        self._details_container.visible = not self._collapsed
        
        main_column = ft.Column([label, self._details_container], spacing=6)

        # Return plain column.
        return main_column

    def refresh_preview(self):
        """Update preview controls without reconstructing content."""
        # Update config field
        if hasattr(self, 'config_field') and self.config_field:
            cfg_val = safe_json_serialize(self.module.config)
            if self.config_field.value != cfg_val:
                self.config_field.value = cfg_val
                safe_update(self.config_field)
        
        # If this view is a body item, reflect parent's preview status/nested preview first
        if (
            getattr(self, 'parent_view', None)
            and getattr(self.parent_view, 'module', None)
            and getattr(self.parent_view.module, '_body_preview', None)
            and self in getattr(self.parent_view, 'body_views', [])
        ):
            try:
                idx = self.parent_view.body_views.index(self)
                preview = self.parent_view.module._body_preview
                if idx < len(preview) and preview[idx] is not None:
                    # status (queued/running/done/error)
                    status = preview[idx].get('status')
                    if status:
                        color_map = {"idle": "grey", "queued": "grey", "running": "blue", "done": "green", "error": "red"}
                        self.set_status(status, color_map.get(status, "grey"))
                    # nested preview propagation for nested ForEach
                    nested = preview[idx].get('nested_preview')
                    if nested and hasattr(self.module, '_body_preview'):
                        import copy
                        try:
                            self.module._body_preview = copy.deepcopy(nested)
                        except Exception:
                            self.module._body_preview = nested
            except Exception:
                pass

        # Build input and propagated displays using builder
        builder = ViewComponentBuilder(self)

        # Update input display
        if hasattr(self, '_input_display_container'):
            self._input_display_container.content = builder.build_input_display(
                self.show_input, self.toggle_input
            ).content
            safe_update(self._input_display_container)

        # Update propagated display
        if hasattr(self, '_propagated_display_container'):
            self._propagated_display_container.content = builder.build_propagated_display(
                self.show_propagated, self.toggle_propagated
            ).content
            safe_update(self._propagated_display_container)

        # Refresh child views for ForEach modules
        if self.body_views:
            for bv in self.body_views:
                bv.refresh_preview()
            if hasattr(self, '_body_views_column'):
                safe_update(self._body_views_column)
    
    def _build_inline_config_controls(self):
        """Auto-generate inline config controls using builder."""
        if not hasattr(self, '_config_controls_container'):
            self._config_controls_container = ft.Row([], spacing=8)
        
        builder = ViewComponentBuilder(self)
        new_controls = builder.build_inline_config_controls(
            self._config_handler.on_inline_bool_change,
            self._config_handler.on_inline_number_change,
            self._config_handler.on_inline_text_change
        )
        
        self._config_controls_container.controls = new_controls.controls
        safe_update(self._config_controls_container)
    
    def toggle_input(self, e=None):
        """Toggle input preview visibility."""
        self.show_input = not self.show_input
        builder = ViewComponentBuilder(self)
        self._input_display_container.content = builder.build_input_display(
            self.show_input, self.toggle_input
        ).content
        safe_update(self._input_display_container)
        self.update()
    
    def toggle_propagated(self, e=None):
        """Toggle propagated output preview visibility."""
        self.show_propagated = not self.show_propagated
        builder = ViewComponentBuilder(self)
        self._propagated_display_container.content = builder.build_propagated_display(
            self.show_propagated, self.toggle_propagated
        ).content
        safe_update(self._propagated_display_container)


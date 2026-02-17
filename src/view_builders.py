"""UI component builders for PipelineModuleView."""

import json
import flet as ft
from typing import Callable
from view_helpers import (
    safe_json_serialize, get_input_data, get_propagated_data,
    calculate_output_diff, build_diff_spans, get_config_fields
)


class ViewComponentBuilder:
    """Builder for PipelineModuleView UI components."""
    
    def __init__(self, view_instance):
        self.view = view_instance
        self.module = view_instance.module
    
    def build_header_row(self, collapse_btn, output_btn=None, config_btn=None, delete_btn=None) -> ft.Row:
        """Build the header row with controls (includes visible drag handle).

        `output_btn` and `config_btn` are optional and only included when provided.
        """
        items = [
            collapse_btn,
            ft.Text(self.module.name, size=14),
            self.view.status,
            ft.Container(expand=True),
        ]

        if delete_btn:
            items.append(delete_btn)

        if output_btn:
            items.append(output_btn)
        if config_btn:
            items.append(config_btn)

        return ft.Row(items)
    
    def build_types_row(self) -> ft.Row:
        """Build input/output types display."""
        in_types = ", ".join(self.module.input_types) if hasattr(self.module, "input_types") else str(self.module.input_type)
        out_types = ", ".join(self.module.output_types) if hasattr(self.module, "output_types") else str(self.module.output_type)
        in_count = getattr(self.module, "input_count", 1)
        out_count = getattr(self.module, "output_count", 1)
        
        return ft.Row([
            ft.Container(
                ft.Row([
                    ft.Text("Inputs", color='white,0.5'),
                    ft.Text(str(in_count), color='white'),
                    ft.Text(in_types, color='white')
                ]),
                padding=5,
                bgcolor='green, 0.5',
                border_radius=5
            ),
            ft.Container(
                ft.Row([
                    ft.Text("Outputs", color='white,0.5'),
                    ft.Text(str(out_count), color='white'),
                    ft.Text(out_types, color='white')
                ]),
                padding=5,
                bgcolor='blue, 0.5',
                border_radius=5
            ),
        ])
    
    def build_config_row(self, config_field, on_edit_click: Callable | None) -> ft.Row:
        """Build config display row. `on_edit_click` optional — omit edit button when None."""
        children = [
            ft.Text("Config:", size=12, color='white,0.6'),
            ft.Container(config_field, expand=True),
        ]
        if on_edit_click:
            children.append(ft.IconButton(ft.Icons.EDIT, on_click=on_edit_click))
        return ft.Row(children)
    
    def build_input_display(self, show_expanded: bool, toggle_callback: Callable) -> ft.Container:
        """Build input display container."""
        inp, full_inp = get_input_data(self.module, self.view.parent_view, self.view)
        
        if not show_expanded:
            return ft.Container(
                content=ft.Row([
                    ft.Text("Last input: (hidden)"),
                    ft.IconButton(ft.Icons.EXPAND_MORE, on_click=toggle_callback)
                ])
            )
        
        # Expanded view
        in_val = safe_json_serialize(inp)
        
        # Create or update TextField
        if not hasattr(self.view, 'last_input_display') or self.view.last_input_display is None:
            self.view.last_input_display = ft.TextField(
                value=in_val, multiline=True, expand=True, disabled=True, text_size=14
            )
        else:
            self.view.last_input_display.value = in_val
        
        children = [
            ft.Row([
                ft.Text("Last input:"),
                ft.IconButton(ft.Icons.EXPAND_LESS, on_click=toggle_callback)
            ]),
        ]
        
        # Add hint row for accumulated input
        if isinstance(full_inp, dict):
            keys = ", ".join(sorted(full_inp.keys()))
            children.append(ft.Row([ft.Text(f"Full keys: {keys}", size=12, color='white,0.6')]))
        
        children.append(self.view.last_input_display)
        
        return ft.Container(content=ft.Column(children, spacing=4))
    
    def build_propagated_display(self, show_expanded: bool, toggle_callback: Callable) -> ft.Container:
        """Build propagated output display container."""
        prop = get_propagated_data(self.module, self.view.parent_view, self.view)
        inp = getattr(self.module, "last_input", None) or getattr(self.module, "_raw_last_input", None) or {}
        
        added_keys, changed_keys = calculate_output_diff(prop, inp)
        spans = build_diff_spans(added_keys, changed_keys)
        
        if not show_expanded:
            text_content = "Propagated output: (hidden)" if prop else "Propagated output: (none)"
            return ft.Container(
                content=ft.Row([
                    ft.Text(text_content),
                    ft.Container(expand=True),
                    ft.IconButton(ft.Icons.EXPAND_MORE, on_click=toggle_callback)
                ])
            )
        
        # Expanded view
        prop_val = safe_json_serialize(prop)
        
        if not hasattr(self.view, 'propagated_field') or self.view.propagated_field is None:
            self.view.propagated_field = ft.TextField(
                value=prop_val, multiline=True, expand=True, disabled=True, text_size=14
            )
        else:
            self.view.propagated_field.value = prop_val
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(spans=spans),
                    ft.Container(expand=True),
                    ft.IconButton(ft.Icons.EXPAND_LESS, on_click=toggle_callback)
                ]),
                self.view.propagated_field
            ], spacing=4)
        )
    
    def build_foreach_body_container(self, body_views, on_add_module: Callable) -> ft.Container:
        """Build ForEach body container with drag & drop."""

        def _make_body_dropzone(view, idx: int):
            empty = ft.Container(width=260, height=10, bgcolor='transparent')

            def _will_accept(e):
                e.control.content.bgcolor = 'white,0.03' if getattr(e, 'accept', True) else 'red'
                e.control.update()

            def _on_leave(e):
                e.control.content.bgcolor = 'transparent'
                e.control.update()

            def _on_accept(e, insert_idx=idx):
                view._on_accept_body_drop(e, insert_idx)

            return ft.DragTarget(group="module", content=empty, on_will_accept=_will_accept, on_accept=_on_accept, on_leave=_on_leave)

        # Initialize or update drop zone
        if not hasattr(self.view, '_drop_zone_content'):
            self.view._drop_zone_content = ft.Container(
                content=ft.Text(
                    "Drop module here" if not body_views else "Drop to add more",
                    size=11, color='white,0.4', text_align=ft.TextAlign.CENTER,
                ),
                padding=10, border_radius=5,
                border=ft.border.all(1, 'white,0.1'),
                bgcolor='white,0.02',
            )
        else:
            self.view._drop_zone_content.content.value = "Drop module here" if not body_views else "Drop to add more"
        
        # Ensure drop zone exists
        if not hasattr(self.view, '_drop_zone'):
            from view_handlers import DragDropHandler
            handler = DragDropHandler(self.view)
            self.view._drop_zone = ft.DragTarget(
                group="module",
                content=self.view._drop_zone_content,
                on_will_accept=handler.on_will_accept_module,
                on_accept=handler.on_accept_new_module,
                on_leave=handler.on_drag_leave,
            )
        
        # Body views are shown as a plain Column (reordering removed)
        controls_for_column = self.view._body_controls_wrapped() if getattr(self.view, '_mounted', False) else [v for v in body_views]
        # make body list scrollable when many child modules exist
        rl = ft.Column(controls_for_column, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        if not hasattr(self.view, '_body_views_column'):
            self.view._body_views_column = rl
        else:
            try:
                self.view._body_views_column.controls = self.view._body_controls_wrapped()
            except Exception:
                # if fallback Column is used, set raw views
                self.view._body_views_column.controls = [v for v in body_views]
        
        # Add module fallback controls
        if not hasattr(self.view, '_add_choice'):
            self.view._add_choice = "MultiplyModule"
        
        add_row = ft.Row([
            ft.Dropdown(
                width=160,
                value=self.view._add_choice,
                options=[
                    ft.dropdown.Option("IntSource"),
                    ft.dropdown.Option("MultiplyModule"),
                    ft.dropdown.Option("ToStringModule"),
                    ft.dropdown.Option("ForEachModule"),
                    ft.dropdown.Option("FilterModule"),
                    ft.dropdown.Option("TransformModule"),
                ],
                on_change=lambda e: setattr(self.view, '_add_choice', e.control.value),
            ),
            ft.IconButton(ft.Icons.ADD, on_click=lambda e: on_add_module(self.view._add_choice)),
            ft.Container(expand=True),
        ], spacing=6)
        
        body_column = ft.Column([
            ft.Row([
                ft.Text("Body:", size=12, color='white,0.6'),
                ft.Container(expand=True),
                add_row
            ]),
            self.view._drop_zone,
            self.view._body_views_column,
        ], spacing=6)
        
        return ft.Container(
            content=body_column,
            padding=ft.padding.only(left=20),
            border=ft.border.only(left=ft.BorderSide(2, 'purple,0.3')),
        )
    
    def build_inline_config_controls(self, on_bool_change, on_number_change, on_text_change) -> ft.Row:
        """Build inline config controls based on module config schema."""
        fields = get_config_fields(self.module)
        controls = []
        
        for name, typ, val in fields:
            lbl = ft.Text(f"{name}:", size=12, color='white,0.7')
            
            # Use simple if-elif instead of match-case for type checking
            if typ is bool:
                ctrl = ft.Checkbox(
                    value=bool(val),
                    on_change=lambda e, n=name: on_bool_change(n, e.control.value)
                )
            elif typ in (int, float):
                ctrl = ft.TextField(
                    value=str(val),
                    width=100,
                    on_submit=lambda e, n=name, t=typ: on_number_change(n, e.control.value, t),
                    on_change=lambda e, n=name, t=typ: on_number_change(n, e.control.value, t),
                )
            elif typ is str:
                ctrl = ft.TextField(
                    value=str(val),
                    width=160,
                    on_change=lambda e, n=name: on_text_change(n, e.control.value),
                    on_submit=lambda e, n=name: on_text_change(n, e.control.value)
                )
            else:
                # Complex type - read-only
                ctrl = ft.TextField(
                    value=json.dumps(val) if not isinstance(val, str) else val,
                    width=220,
                    disabled=True
                )
            
            controls.append(ft.Row([lbl, ctrl], spacing=8))
        
        return ft.Row(controls, spacing=8) if controls else ft.Row([], spacing=8)

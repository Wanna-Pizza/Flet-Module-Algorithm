import flet as ft
from typing import Callable, Optional




class ModulePalette(ft.Container):
    """Left sidebar palette with draggable module types.

    Optional `on_pick(module_name)` callback is invoked when the user clicks
    a palette item — used to spawn top-level modules.
    """


    def __init__(self, available_modules: list, on_pick: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.available_modules = available_modules
        self.on_pick = on_pick
        self.width = 180
        self.bgcolor = 'white,0.05'
        self.border = ft.border.only(right=ft.BorderSide(1, 'white,0.2'))
        self.padding = 10
        
    def _create_module_icons(self):
        """Create icon mappings for module types."""
        return {
            "IntSource": (ft.Icons.NUMBERS, "green"),
            "MultiplyModule": (ft.Icons.CALCULATE, "blue"),
            "ToStringModule": (ft.Icons.TEXT_FIELDS, "orange"),
            "ForEachModule": (ft.Icons.REPEAT, "purple"),
            "FilterModule": (ft.Icons.FILTER_LIST, "teal"),
            "TransformModule": (ft.Icons.AUTORENEW, "cyan"),
        }
    
    def _content(self):
        icons = self._create_module_icons()
        draggables = []
        
        for module_cls in self.available_modules:
            module_name = module_cls.__name__
            icon_name, color = icons.get(module_name, (ft.Icons.WIDGETS, "grey"))
            
            # Create the visual content for the module (clickable to add)
            module_content = ft.Container(
                content=ft.Row([
                    ft.Icon(icon_name, size=20, color=color),
                    ft.Text(
                        module_name.replace("Module", ""),
                        size=13,
                        weight=ft.FontWeight.W_500,
                    ),
                ], spacing=8),
                padding=8,
                border_radius=8,
                bgcolor='white,0.08',
                border=ft.border.all(1, 'white,0.15'),
                on_click=(lambda e, n=module_name: self._handle_pick(n)),
                data=module_name,
            )

            
            # Create semi-transparent feedback during drag
            feedback_content = ft.Container(
                content=ft.Row([
                    ft.Icon(icon_name, size=20, color=color),
                    ft.Text(
                        module_name.replace("Module", ""),
                        size=13,
                        weight=ft.FontWeight.W_500,
                    ),
                ], spacing=8),
                padding=8,
                border_radius=8,
                bgcolor='white,0.3',
                border=ft.border.all(2, color),
                opacity=0.7,
            )
            
            # Create content shown when dragging (slightly dimmed)
            when_dragging_content = ft.Container(
                content=ft.Row([
                    ft.Icon(icon_name, size=20, color=color),
                    ft.Text(
                        module_name.replace("Module", ""),
                        size=13,
                        weight=ft.FontWeight.W_500,
                    ),
                ], spacing=8),
                padding=8,
                border_radius=8,
                bgcolor='white,0.03',
                border=ft.border.all(1, 'white,0.1'),
                opacity=0.5,
            )
            
            # Wrap in Draggable
            draggable = ft.Draggable(
                group="module",
                content=module_content,
                content_feedback=feedback_content,
                content_when_dragging=when_dragging_content,
                data=module_name,
            )

            draggables.append(draggable)
        
        return ft.Column([
            ft.Text(
                "Module Palette",
                size=16,
                weight=ft.FontWeight.BOLD,
                color='white,0.8'
            ),
            ft.Container(height=10),
            ft.Text(
                "Click to add to top-level or drag to ForEach body",
                size=11,
                color='white,0.5',
                italic=True,
            ),
            ft.Container(height=10),
            *draggables,
        ], spacing=8, scroll=ft.ScrollMode.AUTO)
    
    def _handle_pick(self, module_name: str):
        if callable(self.on_pick):
            try:
                self.on_pick(module_name)
            except Exception:
                pass

    def did_mount(self):
        self.content = self._content()
        # No special runtime registration needed; draggables expose `data`.
        self.update()
        return super().did_mount()

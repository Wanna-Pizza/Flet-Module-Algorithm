import flet as ft
from modules import Pipeline, IntSource, MultiplyModule, ToStringModule, ForEachModule
from views import PipelineModuleView
from module_palette import ModulePalette
from view_helpers import safe_update, unregister_view


class Main:
    def __init__(self, page: ft.Page):
        self.page = page
        # demo pipeline for debugging: nested ForEach (Outer -> Inner -> Multiply)
        inner_foreach = ForEachModule(name="InnerForEach", body=[
            (MultiplyModule, {"factor": 10}),
        ])
        outer_foreach = ForEachModule(name="OuterForEach", body=[
            inner_foreach,
            (ToStringModule, None),
        ])

        self.pipeline = Pipeline([
            IntSource(config={"start": 1, "count": 3}),
            outer_foreach,
        ])
        # create module views with delete callback for top-level modules
        self.module_views = [PipelineModuleView(m, on_delete_callback=self._on_module_delete) for m in self.pipeline.modules]
        self.main()

    def _on_module_delete(self, view):
        """Remove a top-level module and its view from the pipeline."""
        if view in self.module_views:
            idx = self.module_views.index(view)
            # unregister and remove
            try:
                unregister_view(view)
            except Exception:
                pass
            # remove from view list and pipeline
            self.module_views.pop(idx)
            try:
                self.pipeline.modules.pop(idx)
            except Exception:
                pass
            # update modules view
            if hasattr(self, 'modules_view'):
                self.modules_view.controls = self._wrapped_module_controls()
                safe_update(self.modules_view)
            # ensure page reflects change
            try:
                self.page.update()
            except Exception:
                pass

    def main(self):
        self.input_field = ft.TextField(label="Input (ignored by IntSource)", value="", expand=True)
        self.log_view = ft.Column([], spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self.run_btn = ft.ElevatedButton("Run", on_click=self.on_run)
        
        # Create module palette (click to add top-level modules)
        palette = ModulePalette(available_modules=[
            IntSource,
            MultiplyModule,
            ToStringModule,
            ForEachModule,
        ], on_pick=self._on_palette_pick)

        # Plain (non-reorderable) view for top-level modules
        self.modules_view = ft.Column(
            [mv for mv in self.module_views],
            spacing=6,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        def _on_drop_will_accept(e):
            e.control.content.bgcolor = 'white,0.06' if getattr(e, 'accept', True) else 'red'
            e.control.update()
            return True

        def _on_drop_leave(e):
            e.control.content.bgcolor = 'white,0.02'
            e.control.update()

        # Prominent drop field above modules list
        self._modules_top_drop = ft.DragTarget(
            group="module",
            content=ft.Container(
                ft.Row([
                    ft.Icon(ft.Icons.ADD_BOX, size=18, color='white,0.6'),
                    ft.Text("Drop module here" if not self.module_views else "Drop to add more", size=13, color='white,0.7')
                ], alignment=ft.MainAxisAlignment.CENTER),
                height=56,
                padding=ft.padding.symmetric(horizontal=12),
                border_radius=8,
                border=ft.border.all(1, 'white,0.12'),
                bgcolor='white,0.02',
                alignment=ft.alignment.center
            ),
            on_will_accept=_on_drop_will_accept,
            on_accept=self._on_modules_drop,
            on_leave=_on_drop_leave,
        )

        middle_column = ft.Column([
            ft.Row([self.input_field, self.run_btn]),
            ft.Container(height=8),
            ft.Text("Modules:"),
            self._modules_top_drop,
            ft.Container(
                expand=True,
                content=ft.DragTarget(
                    group="module",
                    content=self.modules_view,
                    on_will_accept=_on_drop_will_accept,
                    on_accept=self._on_modules_drop,
                    on_leave=_on_drop_leave,
                ),
            ),
        ], expand=True)

        right_column = ft.Column([
            ft.Text("Log:"),
            ft.Container(self.log_view, expand=True)
        ], width=360)

        # Layout: Palette | Modules | Log
        self.page.add(ft.Row([
            palette,
            ft.VerticalDivider(width=1, color='white,0.2'),
            middle_column,
            ft.VerticalDivider(width=1, color='white,0.2'),
            right_column
        ], expand=True))
        self.page.window.always_on_top = True
        self.page.update()
        # ensure modules view reflects current module_views (reordering removed)
        try:
            self.modules_view.controls = [mv for mv in self.module_views]
            safe_update(self.modules_view)
        except Exception:
            pass

    # ------------------ palette pick + modules (reordering removed) ------------------
    def _wrapped_module_controls(self):
        """Return simple list of module view controls (reordering removed)."""
        return [mv for mv in self.module_views]

    def _on_palette_pick(self, module_name: str):
        """Add a top-level module when user clicks an item in the palette."""
        try:
            from view_helpers import get_module_class
            module_cls = get_module_class(module_name)
            if module_cls is None:
                return
            mod = module_cls()
            self.pipeline.modules.append(mod)
            view = PipelineModuleView(mod, on_delete_callback=self._on_module_delete)
            self.module_views.append(view)
            # update modules view
            if hasattr(self, 'modules_view'):
                self.modules_view.controls = self._wrapped_module_controls()
                safe_update(self.modules_view)
            self.page.update()
        except Exception:
            pass

    def _on_modules_drop(self, e):
        """Handle drops onto the top-level drop field: spawn or move modules.

        Uses verbose logging and a fallback resolver to handle slightly-mismatched
        module name strings coming from drag events.
        """
        # initial debug log
        try:
            self.append_log(f"Drop event received: data={getattr(e, 'data', None)!r}, src_id={getattr(e, 'src_id', None)!r}")
        except Exception:
            pass

        from view_helpers import extract_module_name_from_drag_event
        module_name = extract_module_name_from_drag_event(e)
        data = module_name or getattr(e, 'data', None)

        try:
            from view_helpers import get_module_class, register_modules, get_view_by_id

            # 1) Palette add using module name string (with fallback resolution)
            if isinstance(data, str):
                module_cls = get_module_class(data)

                if module_cls is None:
                    # attempt fuzzy/resilient match against registered module names
                    nm = (data or '').strip()
                    candidates = [k for k in register_modules().keys() if k.lower() == nm.lower() or nm.lower() in k.lower() or k.lower() in nm.lower()]
                    if candidates:
                        resolved = candidates[0]
                        module_cls = get_module_class(resolved)
                        self.append_log(f"Resolved drop name '{data}' -> '{resolved}' (fallback)")

                if module_cls is not None:
                    mod = module_cls()
                    self.pipeline.modules.append(mod)
                    view = PipelineModuleView(mod, on_delete_callback=self._on_module_delete)
                    self.module_views.append(view)
                    if hasattr(self, 'modules_view'):
                        self.modules_view.controls = self._wrapped_module_controls()
                        safe_update(self.modules_view)
                    self.append_log(f"Spawned {module_cls.__name__} (drop)")
                    try:
                        if hasattr(self, '_modules_top_drop'):
                            self._modules_top_drop.content.content.controls[1].value = "Drop to add more"
                            self._modules_top_drop.update()
                    except Exception:
                        pass
                    self.page.update()
                    return

                # diagnostic if unable to resolve
                try:
                    self.append_log(f"Unknown module name from drop: {data!r}; available: {list(register_modules().keys())}")
                except Exception:
                    pass

            # 2) Move existing view into top-level (if numeric id provided)
            try:
                src_id = int(data)
            except Exception:
                src_id = None

            if src_id is not None:
                src_view = get_view_by_id(str(src_id))
                if src_view and src_view not in self.module_views:
                    parent_view = getattr(src_view, 'parent_view', None)
                    if parent_view and hasattr(parent_view, 'body_views'):
                        try:
                            idx = parent_view.body_views.index(src_view)
                            parent_view.body_views.pop(idx)
                            parent_view.module.body.pop(idx)
                            if hasattr(parent_view, '_body_views_column'):
                                parent_view._body_views_column.controls = parent_view._body_controls_wrapped()
                                safe_update(parent_view._body_views_column)
                        except Exception:
                            pass

                    src_view.parent_view = None
                    src_view.on_delete_callback = self._on_module_delete
                    self.pipeline.modules.append(src_view.module)
                    self.module_views.append(src_view)
                    if hasattr(self, 'modules_view'):
                        self.modules_view.controls = self._wrapped_module_controls()
                        safe_update(self.modules_view)
                    self.append_log(f"Moved module {getattr(src_view.module, 'name', src_view.module.__class__.__name__)} to top-level")
                    self.page.update()
                    return

        except Exception as exc:
            self.append_log(f"Drop error: {exc}")



    def append_log(self, msg: str):
        print(msg)  # Also print to console
        self.log_view.controls.append(ft.Text(msg, size=12))
        # update only the log container (faster than full page update)
        if getattr(self.log_view, "page", None):
            self.log_view.update()
        else:
            self.page.update()

    def on_run(self, e):
        self.run_btn.disabled = True
        # update only the Run button state
        if getattr(self.run_btn, "page", None):
            self.run_btn.update()

        for mv in self.module_views:
            mv.set_status("queued", "grey")

        def logger(msg: str):
            print(msg)  # Also print to console
            self.append_log(msg)

        async def background_async():
            try:
                for mv in self.module_views:
                    mv.set_status("running", "blue")
                # individual module status widgets update themselves in set_status()

                def on_module_output(module, output):
                    for mv in self.module_views:
                        if mv.module is module:
                            mv.refresh_preview()
                            break

                # ---- DEBUG: dump pipeline/module structure before run ----
                logger("DEBUG: pipeline module structure:")
                def _dump_spec(spec, indent=1):
                    pad = '  ' * indent
                    # tuple spec (Class, config)
                    if isinstance(spec, tuple):
                        cls, cfg = spec
                        logger(f"{pad}{cls.__name__} (config={cfg})")
                        if isinstance(cfg, dict) and 'body' in cfg and isinstance(cfg['body'], list):
                            for s in cfg['body']:
                                _dump_spec(s, indent+1)
                    # module instance with `body` attr
                    elif hasattr(spec, 'body'):
                        logger(f"{pad}{spec.__class__.__name__} instance (name={getattr(spec,'name', None)})")
                        for s in getattr(spec, 'body', []):
                            _dump_spec(s, indent+1)
                    # class object
                    elif isinstance(spec, type):
                        logger(f"{pad}{spec.__name__}")
                    else:
                        logger(f"{pad}{repr(spec)}")

                for m in self.pipeline.modules:
                    _dump_spec(m)
                logger('---- end structure ----')

                result = await self.pipeline.run(None, logger=logger, on_module_output=on_module_output)

                # post-run debug: show module outputs / ForEach previews
                for m in self.pipeline.modules:
                    try:
                        logger(f"MODULE_DEBUG: {getattr(m,'name', m.__class__.__name__)} -> last_output={getattr(m,'last_output', None)} propagated_output={getattr(m,'propagated_output', None)} _body_preview={getattr(m,'_body_preview', None)}")
                    except Exception:
                        pass
                logger(f"Pipeline result: {result}")
                for mv in self.module_views:
                    mv.set_status("done", "green")
            except Exception as exc:
                logger(f"Pipeline error: {exc}")
                for mv in self.module_views:
                    mv.set_status("error", "red")
            finally:
                self.run_btn.disabled = False
                self.run_btn.update()

        self.page.run_task(background_async)


def main(page: ft.Page):
    Main(page)

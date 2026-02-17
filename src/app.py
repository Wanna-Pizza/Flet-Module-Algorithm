import flet as ft
from modules import Pipeline, IntSource, MultiplyModule, ToStringModule, ForEachModule
from views import PipelineModuleView
from module_palette import ModulePalette
from view_helpers import safe_update, unregister_view


class Main:
    def __init__(self, page: ft.Page):
        self.page = page
        # demo pipeline with ForEach to test visual nesting
        foreach_module = ForEachModule(name="ForEach", body=[
            (MultiplyModule, {"factor": 10}),
            (ToStringModule, None),
        ])
        
        self.pipeline = Pipeline([
            IntSource(config={"start": 1, "count": 5}),
            foreach_module,
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
        middle_column = ft.Column([
            ft.Row([self.input_field, self.run_btn]),
            ft.Container(height=8),
            ft.Text("Modules:"),
            ft.Container(self.modules_view, expand=True),
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



    def append_log(self, msg: str):
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

                result = await self.pipeline.run(None, logger=logger, on_module_output=on_module_output)
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

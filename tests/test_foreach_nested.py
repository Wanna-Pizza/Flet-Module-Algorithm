import sys
import asyncio

sys.path.insert(0, 'src')

from modules import Pipeline, IntSource, ForEachModule, MultiplyModule
from views import PipelineModuleView


def test_nested_foreach_with_instance():
    """Outer ForEach contains an inner ForEach instance -> inner Multiply runs."""
    inner = ForEachModule(body=[(MultiplyModule, {"factor": 10})])
    outer = ForEachModule(body=[inner])

    p = Pipeline([
        IntSource(config={"start": 1, "count": 3}),
        outer,
    ])

    out = asyncio.run(p.run(None))
    assert out == [[10.0], [20.0], [30.0]]


def test_nested_foreach_with_tuple_spec():
    """Outer ForEach contains a (ForEachModule, config) spec -> inner Multiply runs."""
    outer = ForEachModule(body=[(ForEachModule, {"body": [(MultiplyModule, {"factor": 10})]})])
    p = Pipeline([
        IntSource(config={"start": 1, "count": 3}),
        outer,
    ])

    out = asyncio.run(p.run(None))
    assert out == [[10.0], [20.0], [30.0]]


def test_move_view_into_foreach_preserves_body():
    """Simulate dragging a ForEach view into another ForEach and ensure its body is preserved."""
    inner = ForEachModule(body=[(MultiplyModule, {"factor": 10})])
    inner_view = PipelineModuleView(inner)

    outer = ForEachModule(body=[])
    outer_view = PipelineModuleView(outer)

    class E:
        pass

    e = E()
    e.data = str(id(inner_view))  # _on_accept_body_drop treats numeric string as src_id
    # call handler as if inserting at index 0
    outer_view._on_accept_body_drop(e, 0)

    assert len(outer.body) == 1
    spec = outer.body[0]
    assert isinstance(spec, tuple)
    cls, cfg = spec
    assert cls is ForEachModule
    assert isinstance(cfg, dict)
    assert 'body' in cfg and cfg['body'][0][0] is MultiplyModule


def test_ui_add_inner_foreach_and_then_add_multiply_persists_to_parent():
    """Simulate adding inner ForEach via UI then adding Multiply inside it — parent spec should include body."""
    # start with outer ForEach that has an inner ForEach added via the view helper
    outer = ForEachModule(body=[])
    outer_view = PipelineModuleView(outer)

    # simulate user adding an inner ForEach from the palette into outer's body
    outer_view._add_module_by_name('ForEachModule')
    assert len(outer.body) == 1

    # get inner child view and add Multiply into its body via UI helper
    inner_view = outer_view.body_views[0]
    inner_view._add_module_by_name('MultiplyModule')

    # simulate user editing the Multiply config inline (set factor to 10)
    inner_child_view = inner_view.body_views[0]
    from view_handlers import ConfigHandler
    ch = ConfigHandler(inner_child_view)
    ch.on_inline_number_change('factor', '10', float)

    # parent spec must be updated so processing uses the updated body/config
    spec = outer.body[0]
    assert isinstance(spec, tuple)
    cls, cfg = spec
    assert cls is ForEachModule
    assert isinstance(cfg, dict)
    assert 'body' in cfg and cfg['body'][0][0] is MultiplyModule
    # config should have been propagated to the top-level spec
    assert cfg['body'][0][1].get('factor') == 10

    # finally, run pipeline to ensure Multiply actually executes with factor 10
    p = Pipeline([
        IntSource(config={"start": 1, "count": 3}),
        outer,
    ])
    out = asyncio.run(p.run(None))
    assert out == [[10.0], [20.0], [30.0]]

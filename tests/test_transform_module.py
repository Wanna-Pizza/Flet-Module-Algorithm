import sys
import asyncio

sys.path.insert(0, 'src')

from modules import TransformModule, Pipeline, IntSource, ForEachModule


def test_transform_square_list():
    t = TransformModule(config={"expr": "x * x"})
    assert t.process([1, 2, 3]) == [1, 4, 9]


def test_transform_dict_field():
    t = TransformModule(config={"expr": "x.upper()", "field": "name"})
    inp = [{"name": "a"}, {"name": "bb"}]
    out = t.process(inp)
    assert out == [{"name": "A"}, {"name": "BB"}]


def test_transform_in_foreach_pipeline():
    # IntSource -> ForEach(Transform) should multiply each element
    outer = ForEachModule(body=[(TransformModule, {"expr": "x * 10"})])
    p = Pipeline([
        IntSource(config={"start": 1, "count": 3}),
        outer,
    ])
    out = asyncio.run(p.run(None))
    assert out == [10, 20, 30]


def test_transform_safe_eval_no_builtins():
    t = TransformModule(config={"expr": "__import__('os').system('echo hi')"})
    # expression must not execute; original values should be preserved
    assert t.process([1, 2]) == [1, 2]

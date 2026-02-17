import sys
import asyncio

sys.path.insert(0, 'src')

from modules import Pipeline, IntSource, FilterModule


def test_filter_even_numbers():
    f = FilterModule(config={"expr": "x % 2 == 0", "mode": "keep"})
    inp = [1, 2, 3, 4, 5]
    out = f.process(inp)
    assert out == [2, 4]


def test_filter_by_field():
    f = FilterModule(config={"expr": "x >= 10", "field": "a"})
    inp = [{"a": 5}, {"a": 12}, {"a": 9}]
    out = f.process(inp)
    assert out == [{"a": 12}]


def test_filter_in_pipeline_after_intsource():
    p = Pipeline([
        IntSource(config={"start": 1, "count": 5}),
        FilterModule(config={"expr": "x > 2", "mode": "keep"}),
    ])
    out = asyncio.run(p.run(None))
    assert out == [3, 4, 5]


def test_filter_bad_expr_is_safe():
    f = FilterModule(config={"expr": "import os; os.system('echo hi')"})
    assert f.process([1, 2, 3]) == []

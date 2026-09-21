"""Template plugin smoke test."""

from __future__ import annotations

from core.plugin_sdk import ResultStatus


def test_template_tool_runs() -> None:
    import logging
    import threading

    from plugin import MyTool  # type: ignore[import-not-found]

    from core.task import ExecutionContext

    context = ExecutionContext(
        task_id="t",
        tool_id="my_tool",
        logger=logging.getLogger("tests.template"),
        cancel_event=threading.Event(),
    )
    result = MyTool().run({"input": "hello"}, context)
    assert result.status is ResultStatus.SUCCESS

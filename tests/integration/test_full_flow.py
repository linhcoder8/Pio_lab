"""End-to-end: nhận message → Chief of Staff → department → output."""

import pytest


@pytest.mark.asyncio
async def test_simple_research_flow():
    """User hỏi research → Optics worker trả lời → output."""
    # TODO Phase 1
    pass


@pytest.mark.asyncio
async def test_qa_replan_loop():
    """Output fail QA → replan → retry → pass."""
    # TODO Phase 1
    pass

"""Application entrypoint."""

from __future__ import annotations

from pio_lab.layer2_runtime.openclaw import create_app

app = create_app()


def main() -> None:
    """CLI entrypoint placeholder."""
    import uvicorn

    uvicorn.run("pio_lab.main:app", host="127.0.0.1", port=8000, reload=True)


__all__ = ["app", "main"]

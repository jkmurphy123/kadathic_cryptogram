"""CLI entry point for Kadathic Cryptogram."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Kadathic Cryptogram — cipher generator and AI-powered solver"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to frontend.yaml config file",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("CRYPTOGRAM_HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CRYPTOGRAM_PORT", "8080")),
        help="Port to listen on (default: 8080)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload for development",
    )
    args = parser.parse_args(argv)

    from kadathic_cryptogram.app import create_app
    from kadathic_cryptogram.config import load_frontend_config

    config = load_frontend_config(args.config) if args.config else None
    create_app(config=config)

    from nicegui import ui

    ui.run(
        host=args.host,
        port=args.port,
        reload=args.reload,
        title="Kadathic Cryptogram",
    )


if __name__ == "__main__":
    main()

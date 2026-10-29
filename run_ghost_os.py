"""CLI runner for GHOST.OS telemetry and diagnostic server."""

import argparse
import sys
import uvicorn


def main():
    parser = argparse.ArgumentParser(
        description="GHOST.OS — The Machine Remembers: Real-Time Telemetry & Diagnostic Interface"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    print("=" * 64)
    print("  GHOST.OS // The Machine Remembers")
    print("  Protocol: ghost.v1  |  Telemetry: 10 Hz")
    print(f"  Access Terminal: http://{args.host}:{args.port}/")
    print("=" * 64)

    uvicorn.run(
        "ghost_os.server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

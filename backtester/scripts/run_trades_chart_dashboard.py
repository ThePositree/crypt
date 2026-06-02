#!/usr/bin/env python3
"""Launch the trade candles Streamlit dashboard."""

import subprocess
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    dashboard_script = script_dir / "trades_chart_dashboard.py"

    if not dashboard_script.exists():
        print("❌ trades_chart_dashboard.py not found!")
        print(f"Expected: {dashboard_script}")
        sys.exit(1)

    print("📊 Starting Trade Candles Viewer...")
    print("   URL: http://localhost:8502")
    print("   Stop with Ctrl+C")
    print("-" * 50)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dashboard_script),
                "--server.port",
                "8502",
                "--server.address",
                "localhost",
                "--browser.gatherUsageStats",
                "false",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

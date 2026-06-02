#!/usr/bin/env python3
"""
Скрипт для запуска Streamlit dashboard
"""

import os
import subprocess
import sys


def main():
    print("🚀 Запуск Backtester Analysis Dashboard...")
    print("📊 Streamlit будет доступен по адресу: http://localhost:8501")
    print("💡 Для остановки нажмите Ctrl+C")
    print("-" * 50)

    try:
        # Запускаем streamlit
        script_dir = os.path.dirname(os.path.abspath(__file__))
        streamlit_app = os.path.join(script_dir, "streamlit_app.py")

        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                streamlit_app,
                "--server.port",
                "8501",
                "--server.address",
                "0.0.0.0",
                "--browser.gatherUsageStats",
                "false",
            ]
        )
    except KeyboardInterrupt:
        print("\n👋 Dashboard остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")


if __name__ == "__main__":
    main()

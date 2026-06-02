#!/usr/bin/env python3
"""
Скрипт для запуска продвинутого дашборда анализа торговых стратегий
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Запускает продвинутый дашборд"""

    # Получаем путь к скрипту дашборда
    script_dir = Path(__file__).parent
    dashboard_script = script_dir / "advanced_dashboard.py"

    if not dashboard_script.exists():
        print("❌ Файл advanced_dashboard.py не найден!")
        print(f"Ожидаемый путь: {dashboard_script}")
        sys.exit(1)

    print("🚀 Запуск Advanced Trading Strategy Dashboard...")
    print("📊 Дашборд будет доступен по адресу: http://localhost:8501")
    print("💡 Для остановки нажмите Ctrl+C")
    print("-" * 50)

    try:
        # Запускаем streamlit
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dashboard_script),
                "--server.port",
                "8501",
                "--server.address",
                "localhost",
                "--browser.gatherUsageStats",
                "false",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n👋 Дашборд остановлен пользователем")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска дашборда: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

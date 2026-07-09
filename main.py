import asyncio
import os
import platform
import sys
import traceback

import qasync
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMessageBox

import config
from gui import MainWindow

APP_NAME = "TelegramAutoBot"


def resolve_application_font(fallback_family="SF Pro Display", fallback_size=11):
    try:
        font = QFont()
        if fallback_family:
            font.setFamily(fallback_family)
        font.setPointSize(fallback_size)
        if font.family():
            return font
    except Exception:
        pass
    return QFont()


def setup_macos():
    if platform.system() == 'Darwin':
        os.environ['QT_MAC_WANTS_LAYER'] = '1'
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
        os.environ['QT_QUICK_BACKEND'] = 'software'
        os.environ['PYTHONASYNCIODEBUG'] = '0'
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        print("✅ macOS оптимизации применены")


def get_app_dir():
    return config.get_app_dir()


def show_error(title, message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec()


async def async_main():
    await asyncio.sleep(0.1)
    window = MainWindow()
    window.show()
    return window


def main():
    try:
        os.chdir(get_app_dir())

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)

        setup_macos()

        font = resolve_application_font("SF Pro Display", 11)
        app.setFont(font)

        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        startup_task = None
        window_holder = {}

        def _shutdown_loop():
            nonlocal startup_task
            try:
                if startup_task and not startup_task.done():
                    startup_task.cancel()
                for task in list(asyncio.all_tasks(loop)):
                    if task is not asyncio.current_task():
                        task.cancel()
            except Exception:
                pass
            try:
                if loop.is_running():
                    loop.stop()
            except Exception:
                pass
            try:
                if not loop.is_closed():
                    loop.close()
            except Exception:
                pass

        def _on_startup_done(task):
            nonlocal startup_task
            if task.cancelled():
                return
            exc = task.exception()
            if exc is not None:
                show_error(
                    "Ошибка запуска",
                    "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                )
                _shutdown_loop()
            else:
                window_holder["window"] = task.result()

        app.aboutToQuit.connect(_shutdown_loop)

        with loop:
            startup_task = loop.create_task(async_main())
            startup_task.add_done_callback(_on_startup_done)
            loop.run_forever()

    except Exception:
        show_error("Критическая ошибка", traceback.format_exc())


if __name__ == "__main__":
    main()

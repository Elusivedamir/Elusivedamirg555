import os
import sys
import platform
import traceback
import asyncio

# ===== ФИКСЫ ДЛЯ macOS =====
if platform.system() == 'Darwin':
    os.environ['QT_MAC_WANTS_LAYER'] = '1'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
    os.environ['QT_QUICK_BACKEND'] = 'software'
    os.environ['PYTHONASYNCIODEBUG'] = '0'

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import qasync
from gui import MainWindow

APP_NAME = "TelegramAutoBot"

def setup_macos():
    if platform.system() == 'Darwin':
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        print("✅ macOS оптимизации применены")

def get_app_dir():
    path = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return path

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
        
        font = QFont("SF Pro Display", 11)
        app.setFont(font)
        
        # ===== ИСПРАВЛЕНИЕ ДЛЯ ASYNCIO =====
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        window_holder = {}
        
        def _on_startup_done(task):
            if task.cancelled():
                return
            exc = task.exception()
            if exc is not None:
                show_error(
                    "Ошибка запуска",
                    "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                )
                loop.stop()
            else:
                window_holder["window"] = task.result()
        
        with loop:
            startup_task = loop.create_task(async_main())
            startup_task.add_done_callback(_on_startup_done)
            loop.run_forever()
            
    except Exception as e:
        show_error("Критическая ошибка", traceback.format_exc())

if __name__ == "__main__":
    main()

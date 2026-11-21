"""TubeGet 실행 진입점."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from tubeget import APP_NAME
from tubeget.single_instance import InstanceServer, notify_running_instance
from tubeget.ui.main_window import MainWindow
from tubeget.ui.theme import app_icon, apply_theme


def main() -> int:
    if sys.platform == "win32":
        try:  # 작업 표시줄에 파이썬 아이콘 대신 앱 아이콘 표시
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TubeGet.App")
        except Exception:  # noqa: BLE001
            pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(True)
    if notify_running_instance():
        return 0  # 이미 켜져 있는 창을 앞으로 가져옴
    server = InstanceServer(app)
    apply_theme(app)
    win = MainWindow()
    server.activated.connect(win._raise)
    win.show()
    code = app.exec()
    # 창 → 앱 순서로 확실히 정리 (파이썬 종료 시 정리 순서가 꼬여 튕기는 것 방지)
    win.hide()
    win.deleteLater()
    app.processEvents()
    del win, server
    return code


if __name__ == "__main__":
    sys.exit(main())

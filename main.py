"""TubeGet 실행 진입점."""
import os
import sys

# 어느 폴더에서 실행하든 이 파일 옆의 tubegetapp 폴더를 찾도록
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

try:
    from tubegetapp import APP_NAME
    from tubegetapp.single_instance import InstanceServer, notify_running_instance
    from tubegetapp.ui.main_window import MainWindow
    from tubegetapp.ui.theme import app_icon, apply_theme
except ModuleNotFoundError as exc:  # 압축이 덜 풀렸거나 폴더가 섞인 경우
    if "tubegetapp" not in str(exc):
        raise
    _app = QApplication(sys.argv)
    QMessageBox.critical(
        None, "TubeGet",
        "프로그램 파일(tubegetapp 폴더)을 찾을 수 없어요.\n\n"
        "압축 파일을 마우스 오른쪽 → '모두 압축 풀기'로 새 폴더에 전부 푼 다음,\n"
        "그 폴더 안의 run_windows.bat 으로 실행해 주세요.\n"
        "(예전 버전 폴더 위에 덮어서 풀면 이런 문제가 생길 수 있어요)\n\n"
        f"찾은 위치: {os.path.dirname(os.path.abspath(__file__))}")
    sys.exit(1)


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

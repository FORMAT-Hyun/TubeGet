"""pytest 공통 설정.

macOS 의 CI 에서 모든 테스트가 통과한 뒤에도 파이썬이 끝나면서 Qt 객체를 정리하다가
비정상 종료(segfault)하는 경우가 있다.
- 끝날 때 남은 창을 먼저 닫고 지운다.
- ACORTUBE_FAST_EXIT=1 이고 Windows 가 아니면, 결과 출력이 끝난 뒤 바로 프로세스를 끝내서
  테스트 결과(종료 코드)만 그대로 돌려준다. (Windows 의 os._exit 는 DLL 정리를 그대로 해서 오히려 위험)
"""
import os
import sys


def _close_qt_windows() -> None:
    try:
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return
    app = QApplication.instance()
    if not isinstance(app, QApplication):   # 창 없는 QCoreApplication 이면 닫을 창도 없다
        return
    for w in list(QApplication.topLevelWidgets()):
        w.close()
        w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def pytest_sessionfinish(session, exitstatus):
    session.config._acortube_exitstatus = int(exitstatus)
    _close_qt_windows()


def pytest_unconfigure(config):
    status = getattr(config, "_acortube_exitstatus", None)
    if status is None or os.environ.get("ACORTUBE_FAST_EXIT") != "1" or sys.platform == "win32":
        return
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(status)

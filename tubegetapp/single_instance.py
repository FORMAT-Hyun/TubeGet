"""프로그램이 두 개 켜지지 않게: 이미 켜져 있으면 그 창을 앞으로 가져온다."""
from __future__ import annotations

import hashlib
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from .paths import data_dir


def server_name() -> str:
    # 사용자/데이터 폴더마다 다른 이름 (다른 계정끼리는 서로 막지 않음)
    digest = hashlib.md5(str(data_dir()).encode("utf-8")).hexdigest()[:12]
    return f"Acortube-{digest}"


def notify_running_instance() -> bool:
    """이미 실행 중인 Acortube가 있으면 창을 띄우라고 알리고 True."""
    sock = QLocalSocket()
    sock.connectToServer(server_name())
    if not sock.waitForConnected(500):
        return False
    sock.write(b"activate")
    sock.flush()
    sock.waitForBytesWritten(500)
    sock.disconnectFromServer()
    return True


class InstanceServer(QObject):
    activated = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        name = server_name()
        if not self._server.listen(name):
            # 비정상 종료로 남은 소켓 파일 정리 후 재시도 (맥/리눅스)
            QLocalServer.removeServer(name)
            self._server.listen(name)

    def _on_connection(self) -> None:
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: s.readAll())
            sock.disconnected.connect(sock.deleteLater)
        self.activated.emit()

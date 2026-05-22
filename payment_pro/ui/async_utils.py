from collections.abc import Callable
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    success = pyqtSignal(object)
    error = pyqtSignal(str)
    finished = pyqtSignal()


class ApiWorker(QRunnable):
    def __init__(self, fn: Callable[[], object]):
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.success.emit(self.fn())
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


def run_async(
    fn: Callable[[], object],
    on_success: Callable[[object], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    on_finished: Callable[[], None] | None = None,
) -> ApiWorker:
    worker = ApiWorker(fn)
    if on_success:
        worker.signals.success.connect(on_success)
    if on_error:
        worker.signals.error.connect(on_error)
    if on_finished:
        worker.signals.finished.connect(on_finished)
    QThreadPool.globalInstance().start(worker)
    return worker

from PySide6.QtCore import QObject, Signal

from backend.models.list_model import TaskListModel, TaskStatus


class ScenarioRunner(QObject):
    """
    Проходит по шагам сценария, используя граф options[pass/fail].next.
    Manual-шаги останавливают прогон и ждут report_result() извне (например, из UI).
    Auto-шаги делегируются зарегистрированным обработчикам по testing.kind —
    обработчик сам решает, как получить результат (синхронно или через сигнал/слот),
    и в любом случае обязан вызвать report_result() когда результат готов.
    """

    stepStarted = Signal(str)            # step_id — начали новый шаг
    stepFinished = Signal(str, str)       # step_id, result ('pass'/'fail')
    waitingUser = Signal(str)             # step_id — manual-шаг, ждём действий пользователя
    finished = Signal()                   # прогон остановлен (pause / нет next / нет обработчика)

    def __init__(self, model: TaskListModel, kicad=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.kicad = kicad
        self.current_id = None
        self._running = False
        self._auto_handlers = {}  # kind -> callable(index: QModelIndex)

    def register_auto_handler(self, kind: str, handler):
        """
        handler(index) вызывается для auto-шагов с testing.kind == kind.
        Обработчик не обязан быть синхронным — он может, например, отправить
        команду в SerialPort и вернуться сразу, а report_result() вызвать позже
        из слота, привязанного к сигналу порта.
        """
        self._auto_handlers[kind] = handler

    def is_running(self) -> bool:
        return self._running

    def start(self, start_id: str = None):
        self.current_id = start_id or self.model.start_id
        self._running = True
        self._process_current()

    def resume_from(self, step_id: str):
        self.current_id = step_id
        self._running = True
        self._process_current()

    def stop(self):
        self._running = False

    def _process_current(self):
        if not self._running or self.current_id is None:
            return

        index = self.model.get_index_by_id(self.current_id)
        if index is None:
            print(f"Крок '{self.current_id}' не знайдено, зупинка")
            self._running = False
            self.finished.emit()
            return

        nets = self.model.get_nets(index)
        if nets and self.kicad:
            self.kicad.select_net(*nets, zoomToFit=False)

        self.stepStarted.emit(self.current_id)

        mode = self.model.get_mode(index)

        if mode == "manual":
            self.waitingUser.emit(self.current_id)
            return

        if mode == "auto":
            kind = self.model.get_kind(index)
            handler = self._auto_handlers.get(kind)
            if handler is None:
                print(f"Немає обробника для kind='{kind}', зупинка")
                self._running = False
                self.finished.emit()
                return
            handler(index)
            return

        # info и прочие режимы без проверки — считаем пройденным и идём дальше
        self.report_result("pass")

    def report_result(self, result: str):
        """result: 'pass' или 'fail'. Дергается вручную (manual) или обработчиком auto."""
        if self.current_id is None:
            return

        index = self.model.get_index_by_id(self.current_id)
        if index is None:
            return

        status = TaskStatus.PASSED if result == "pass" else TaskStatus.FAILED
        self.model.set_status(index, status)
        self.stepFinished.emit(self.current_id, result)

        if not self._running:
            return  # прогон остановили, пока ждали результат

        options = self.model.get_options(index)
        step_result = options.get(result, {})
        next_id = step_result.get("next")
        pause = step_result.get("pause", False)

        if pause or not next_id:
            self._running = False
            self.finished.emit()
            return

        self.current_id = next_id
        self._process_current()
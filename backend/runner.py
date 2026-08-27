from enum import Enum

from PySide6.QtCore import QObject, Signal

from backend.models.list_model import TaskListModel, TaskStatus, STATUS_COLORS, STATUS_LABELS, STATUS_ROLE


class DebugState(Enum):
    """Стан дебагу — як у звичайному дебагері IDE."""
    IDLE = "idle"          # ще не запускали / повний Stop
    RUNNING = "running"    # йде автопрогін
    PAUSED = "paused"      # зупинено на кроці (пауза, manual-очікування, fail-breakpoint)
    FINISHED = "finished"  # дійшли до кінця графа (немає next і немає pause)


class ScenarioRunner(QObject):
    """
    Проходит по шагам сценария, используя граф options[pass/fail].next.
    Manual-шаги останавливают відладку и ждут report_result() извне (например, из UI).
    Auto-шаги делегируются зарегистрированным обработчикам по testing.kind —
    обработчик сам решает, как получить результат (синхронно или через сигнал/слот),
    и в любом случае обязан вызвать report_result() когда результат готов.

    Модель дебага — как в дебагере программ:
      start()   — вход в сценарий (с начала или с указанного шага, "Run to here");
      pause()   — приостановить автовідладку, НЕ теряя текущую позицию;
      resume()  — продолжить с того же места (например, шаги options[fail].next,
                  которые ссылаются сами на себя — это "брейкпоинт на ошибке":
                  чинишь плату и жмёшь resume, чтобы перепроверить тот же шаг);
      stop()    — полный сброс текущей позиции (маркер снимается);
      restart() — сбросить все статусы и начать сценарий заново.

    Текущий шаг раннера всегда отражается в модели через model.set_current()
    (маркер вроде "стрелки" на строке в дебагере IDE), а все текстовые статусы
    відладку идут через единый канал debugStatus (см. _status()), с человеко-
    читаемым названием шага (title), а не его техническим id.
    """

    stepStarted = Signal(str)            # step_id — начали новый шаг
    stepFinished = Signal(str, str)       # step_id, result ('pass'/'fail')
    waitingUser = Signal(str)             # step_id — manual-шаг, ждём действий пользователя
    finished = Signal()                   # відладк остановлен (pause / нет next / нет обработчика)
    debugStatus = Signal(str)             # человекочитаемый статус дебага для UI/консоли
    stateChanged = Signal(str)            # DebugState.value — для кнопки Start/Pause и индикаторов в UI

    def __init__(self, model: TaskListModel, kicad=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.kicad = kicad
        self.current_id = None
        self._running = False
        self._state = DebugState.IDLE
        self._auto_handlers = {}  # kind -> callable(index: QModelIndex)

    # ---- Внутренние помощники ----

    def _status(self, msg: str):
        """
        Единая точка вывода статуса дебага. Сейчас — просто в консоль,
        плюс сигнал debugStatus, чтобы позже подключить к UI (статус-бар/лог)
        без изменения логики раннера.
        """
        print(msg)
        self.debugStatus.emit(msg)

    def _set_state(self, state: DebugState):
        if self._state == state:
            return
        self._state = state
        self.stateChanged.emit(state.value)

    def _step_label(self, step_id: str) -> str:
        """Людяне ім'я кроку для логів (title), а не технічний id."""
        if step_id is None:
            return "-"
        index = self.model.get_index_by_id(step_id)
        if index is None:
            return step_id
        return self.model.get_title(index)

    @property
    def state(self) -> DebugState:
        return self._state

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

    # ---- Управление дебагом: Start / Pause / Resume / Stop / Restart ----

    def start(self, start_id: str = None):
        """Вход в сценарий: с начала (model.start_id) либо с указанного шага
        (например, 'Почати перевірку звідси' из контекстного меню)."""
        self.current_id = start_id or self.model.start_id
        self._running = True
        self._set_state(DebugState.RUNNING)
        self._status(f"Дебаг запущено з кроку '{self._step_label(self.current_id)}'")
        self._process_current()

    def resume(self):
        """Продолжить с текущей позиции (после pause() или после fail-паузы)."""
        if self.current_id is None:
            self.start()
            return
        self._running = True
        self._set_state(DebugState.RUNNING)
        self._status(f"Дебаг відновлено з кроку '{self._step_label(self.current_id)}'")
        self._process_current()

    def pause(self):
        """Приостановить автовідладку, не теряя текущую позицию (маркер остаётся)."""
        if not self._running:
            return
        self._running = False
        self._set_state(DebugState.PAUSED)
        self._status(f"Дебаг призупинено на кроці '{self._step_label(self.current_id)}'")

    def toggle_start_pause(self):
        """Одна кнопка Старт/Пауза — как Play/Pause в дебагере IDE."""
        if self._running:
            self.pause()
        elif self.current_id is not None and self._state == DebugState.PAUSED:
            self.resume()
        else:
            self.start()

    def stop(self):
        """Полная остановка: сбрасывает текущую позицию (маркер снимается)."""
        self._running = False
        self._set_state(DebugState.IDLE)
        self._status("Дебаг зупинено оператором")
        self.current_id = None
        self.model.clear_current()

    def restart(self):
        """Сбросить все статусы шагов и начать сценарий заново."""
        self.model.reset_statuses()
        self.model.clear_current()
        self._status("Дебаг перезапущено з початку сценарію")
        self.start()

    def next_step(self):
        """
        Переходит к следующему шагу сценария.
        Если текущий шаг ещё не выполнен (статус NOT_TESTED),
        то переход блокируется до подтверждения оператора.
        Если шаг уже имеет статус PASSED или FAILED - позволяет переход.
        """
        if not self._running or self.current_id is None:
            self._status("відладку не активний або немає поточного кроку")
            return

        index = self.model.get_index_by_id(self.current_id)
        if index is None:
            self._status(f"Крок '{self._step_label(self.current_id)}' не знайдено, зупинка")
            self._running = False
            self._set_state(DebugState.IDLE)
            self.model.clear_current()
            self.finished.emit()
            return

        status = self.model.get_status(index)

        # ВИПРАВЛЕНО: раніше умова була "status != PASSED", через що FAILED
        # теж блокувався і гілка "result = fail" нижче була недосяжним кодом.
        if status not in (TaskStatus.PASSED, TaskStatus.FAILED):
            self._status(f"Крок '{self._step_label(self.current_id)}' ще не виконано — очікується підтвердження оператора")
            return

        options = self.model.get_options(index)
        result = "pass" if status == TaskStatus.PASSED else "fail"

        step_result = options.get(result, {})
        next_id = step_result.get("next")
        pause = step_result.get("pause", False)

        if pause or not next_id:
            self._running = False
            self._set_state(DebugState.PAUSED if pause else DebugState.FINISHED)
            self._status(f"Крок '{self._step_label(self.current_id)}': відладку зупинено (pause/немає наступного кроку)")
            self.finished.emit()
            return

        self.current_id = next_id
        self._process_current()

    def _process_current(self):
        if not self._running or self.current_id is None:
            return

        index = self.model.get_index_by_id(self.current_id)
        if index is None:
            self._status(f"Крок '{self._step_label(self.current_id)}' не знайдено, зупинка")
            self._running = False
            self._set_state(DebugState.IDLE)
            self.model.clear_current()
            self.finished.emit()
            return

        # Підсвічуємо поточний крок в моделі (маркер дебагера)
        self.model.set_current(index)

        nets = self.model.get_nets(index)
        if nets and self.kicad:
            self.kicad.select_net(*nets, zoomToFit=False)

        self.stepStarted.emit(self.current_id)

        mode = self.model.get_mode(index)

        if mode == "manual":
            self._set_state(DebugState.PAUSED)
            self._status(f"Крок '{self._step_label(self.current_id)}' ручний — очікується дія оператора")
            self.waitingUser.emit(self.current_id)
            return

        if mode == "auto":
            kind = self.model.get_kind(index)
            handler = self._auto_handlers.get(kind)
            if handler is None:
                self._status(f"Немає обробника для kind='{kind}', зупинка")
                self._running = False
                self._set_state(DebugState.IDLE)
                self.finished.emit()
                return
            self._set_state(DebugState.RUNNING)
            self._status(f"Крок '{self._step_label(self.current_id)}': автоперевірка kind='{kind}' запущена")
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
        self._status(f"Крок '{self._step_label(self.current_id)}': результат = {result}")

        if not self._running:
            return  # відладку остановили, пока ждали результат

        options = self.model.get_options(index)
        step_result = options.get(result, {})
        next_id = step_result.get("next")
        pause = step_result.get("pause", False)

        if pause or not next_id:
            self._running = False
            # pause=True (например, fail -> next: сам_на_себя) — это "брейкпоинт
            # на ошибке": маркер остаётся на этом шаге, resume() повторит его же.
            # Отсутствие next_id при pause=False — это настоящий конец сценария.
            self._set_state(DebugState.PAUSED if pause else DebugState.FINISHED)
            self._status(f"Крок '{self._step_label(self.current_id)}': відладку зупинено (pause/немає наступного кроку)")
            self.finished.emit()
            return

        self.current_id = next_id
        self._process_current()
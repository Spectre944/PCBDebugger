from enum import Enum

from PySide6.QtCore import QObject, Signal

from backend.models.list_model import (
    TaskListModel,
    TaskStatus,
    STATUS_COLORS,
    STATUS_LABELS,
    STATUS_ROLE,
    STATUS_TO_OPTION_KEY,
)


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
    stepSkipped = Signal(str)             # step_id — крок пропущено оператором (skip_current)
    waitingUser = Signal(str)             # step_id — manual-шаг, ждём действий пользователя
    breakpointHit = Signal(str)           # step_id — зупинились саме через брейкпоінт (fail-graph або user), а не просто Pause
    breakpointsChanged = Signal(str, bool)  # step_id, увімкнено/вимкнено — для позначки в дереві
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
        self._breakpoints: set[str] = set()   # step_id-и, на яких треба зупинитись ПЕРЕД виконанням
        self._breakpoint_bypassed = False     # одноразовий пропуск брейкпоінта (resume()/retry_current())

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

    # ---- Брейкпоінти (точки зупинки ПЕРЕД виконанням конкретного кроку) ----

    def toggle_breakpoint(self, step_id: str):
        """Ставить/знімає брейкпоінт на кроці. Викликається з UI (контекстне
        меню в дереві), а не сценарієм — на відміну від fail-брейкпоінта
        (options[fail].pause=True), який прописаний у самому scenario.json."""
        if step_id in self._breakpoints:
            self._breakpoints.discard(step_id)
            self.breakpointsChanged.emit(step_id, False)
        else:
            self._breakpoints.add(step_id)
            self.breakpointsChanged.emit(step_id, True)

    def has_breakpoint(self, step_id: str) -> bool:
        return step_id in self._breakpoints

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
        self._breakpoint_bypassed = True  # інакше знову впремося у той самий брейкпоінт
        self._running = True
        self._set_state(DebugState.RUNNING)
        self._status(f"Дебаг відновлено з кроку '{self._step_label(self.current_id)}'")
        self._process_current()

    def pause(self):
        """Приостановить автовідладку, не теряя текущую позицию (маркер остаётся).

        ВИПРАВЛЕНО: раніше умовою було "if not self._running", а після
        ручного кроку self._running лишався True (навмисно — щоб next_step()
        працював), хоча стан вже й так PAUSED. Через це перший клік по кнопці
        Старт/Пауза під час очікування ручного кроку тихо "з'їдав" клік
        (виставляв _running=False, хоча ми й так стояли), і toggle_start_pause()
        наступного разу викликав pause() ще раз замість resume() — треба було
        два кліки, щоб реально піти далі. Тепер пауза має сенс лише тоді, коли
        дійсно щось активно виконується (RUNNING); якщо ми вже й так стоїмо
        (ручний крок / fail-брейкпоінт), pause() — no-op.
        """
        if self._state != DebugState.RUNNING:
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

    def retry_current(self):
        """Повторити ПОТОЧНИЙ крок ще раз, не рухаючись по графу.

        На відміну від resume() (яка "повторює той самий крок" лише у
        вузькому випадку fail-брейкпоінта, коли options[fail].next вказує
        сам на себе) — retry_current працює для БУДЬ-ЯКОГО кроку в БУДЬ-ЯКОМУ
        стані (в тому числі якщо шлях кроку в графі веде далі, а не на себе):
        скидає його статус і запускає перевірку заново. Корисно, коли
        причина fail була не в платі (завада на шині, оператор не встиг
        підключити щуп) і сценарій не передбачав тут брейкпоінт.
        """
        if self.current_id is None:
            return
        index = self.model.get_index_by_id(self.current_id)
        if index is None:
            return
        self.model.set_status(index, TaskStatus.NOT_TESTED)
        self._breakpoint_bypassed = True  # не зупинятись знову на тому ж брейкпоінті
        self._running = True
        self._set_state(DebugState.RUNNING)
        self._status(f"Повторний запуск кроку '{self._step_label(self.current_id)}'")
        self._process_current()

    def skip_current(self):
        """Пропустити поточний крок без виконання перевірки.

        Статус — SKIPPED (окремо від PASSED/FAILED), щоб у підсумковому
        звіті було видно, що саме тут перевірку НЕ проводили, а не що вона
        "пройшла". Рух по графу: якщо в options кроку є явний ключ "skip"
        з "next" — йдемо туди; інакше йдемо тим самим маршрутом, що й pass
        (найчастіший випадок — "пропустив, розберусь пізніше").
        """
        if self.current_id is None:
            return
        index = self.model.get_index_by_id(self.current_id)
        if index is None:
            return

        self.model.set_status(index, TaskStatus.SKIPPED)
        self.stepSkipped.emit(self.current_id)
        self._status(f"Крок '{self._step_label(self.current_id)}' пропущено оператором")

        options = self.model.get_options(index)
        step_result = options.get("skip") or options.get("pass", {})
        next_id = step_result.get("next")

        if not next_id:
            self._running = False
            self._set_state(DebugState.FINISHED)
            self.finished.emit()
            return

        self.current_id = next_id
        self._breakpoint_bypassed = False
        self._running = True
        self._set_state(DebugState.RUNNING)
        self._process_current()

    def _advance_from(self, index, result: str):
        """Спільна логіка переходу по графу, коли результат кроку ВЖЕ відомий
        (щойно записаний, або виставлений раніше оператором вручну): дивиться
        options[result], визначає next_id/pause і або зупиняє відладку
        (брейкпоінт/кінець сценарію), або йде на next_id.

        Винесено в окремий метод, бо раніше report_result() і next_step()
        дублювали цю логіку по-різному, і саме це дублювання спричинило
        баг: next_step() зовсім не вмів коректно повідомити про зупинку на
        брейкпоінті (просто вимагав self._running і відмовляв з незрозумілим
        "відладку не активний", навіть коли current_id був цілком нормальний,
        просто попередній крок стояв на fail-брейкпоінті).
        """
        options = self.model.get_options(index)
        step_result = options.get(result, {})
        next_id = step_result.get("next")
        pause = step_result.get("pause", False)

        if pause or not next_id:
            self._running = False
            # pause=True (например, fail -> next: сам_на_себя) — это "брейкпоинт
            # на ошибке": маркер остаётся на этом шаге (current_id НЕ меняем),
            # resume() повторит его же. Отсутствие next_id при pause=False —
            # это настоящий конец сценария.
            if pause:
                # breakpointHit ДО _set_state — так само, як з waitingUser в
                # manual-гілці: UI визначає ПРИЧИНУ паузи саме за цим
                # сигналом, і якщо stateChanged прийде першим, побачить ще
                # стару причину і покаже узагальнене "На паузі" замість
                # "Зупинено на брейкпоінті".
                self.breakpointHit.emit(self.current_id)
            self._set_state(DebugState.PAUSED if pause else DebugState.FINISHED)
            if pause:
                self._status(
                    f"Крок '{self._step_label(self.current_id)}': брейкпоінт — "
                    f"натисніть 'Продовжити' (Старт/Пауза), а не 'Наступний крок'"
                )
            else:
                self._status(f"Крок '{self._step_label(self.current_id)}': сценарій завершено, наступного кроку немає")
            self.finished.emit()
            return

        # ВИПРАВЛЕНО: раніше current_id оновлювався лише якщо self._running
        # було True на момент приходу результату. Якщо оператор встиг
        # натиснути Pause, поки авто-крок ще чекав відповідь по serial, і
        # відповідь приходила вже ПІСЛЯ паузи — current_id лишався на щойно
        # завершеному кроці, і resume() замість переходу далі просто ЗАНОВО
        # запускав уже пройдений крок (повторна відправка команди в порт
        # тощо). Тепер перехід по графу фіксуємо завжди, а от чи продовжувати
        # обробку ПРЯМО ЗАРАЗ — вирішуємо окремо нижче.
        self.current_id = next_id

        if not self._running:
            return  # відладку зупинили (pause), поки чекали результат — далі чекаємо resume()

        self._process_current()

    def next_step(self):
        """
        Переходит к следующему шагу сценария.
        Если текущий шаг ещё не выполнен (статус NOT_TESTED),
        то переход блокируется до подтверждения оператора.
        Если шаг уже имеет статус PASSED/FAILED/SKIPPED - позволяет переход.

        ВИПРАВЛЕНО: раніше умова була "if not self._running or current_id is
        None" — а self._running спеціально стає False саме тоді, коли крок
        FAILED і стоїть на fail-брейкпоінті (options[fail].pause=True). Тобто
        рівно в момент, коли оператор найімовірніше й захоче натиснути
        "Наступний крок" після провалу — метод миттєво відмовляв з
        незрозумілим "відладку не активний або немає поточного кроку", хоча
        сесія була цілком жива. Тепер next_step() потребує лише те, що сесія
        взагалі існує (current_id задано, стан не IDLE); а якщо крок дійсно
        стоїть на брейкпоінті — _advance_from() поверне те саме зрозуміле
        повідомлення "натисніть Продовжити", що й при щойно отриманому fail.
        """
        if self.current_id is None or self._state == DebugState.IDLE:
            self._status("Дебаг не запущено — немає активної сесії")
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

        if status not in (TaskStatus.PASSED, TaskStatus.FAILED, TaskStatus.SKIPPED):
            self._status(f"Крок '{self._step_label(self.current_id)}' ще не виконано — очікується підтвердження оператора")
            return

        result = STATUS_TO_OPTION_KEY.get(status, "pass")
        self._advance_from(index, result)

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

        # Брейкпоінт (поставлений оператором з UI) — зупиняємось ПЕРЕД
        # виконанням кроку, а не після. bypass знімається resume()/
        # retry_current(), інакше ми впремося в той самий брейкпоінт вічно.
        if self.current_id in self._breakpoints and not self._breakpoint_bypassed:
            self._running = False
            self.breakpointHit.emit(self.current_id)  # ДО _set_state — див. коментар у _advance_from
            self._set_state(DebugState.PAUSED)
            self._status(f"Брейкпоінт: зупинено перед кроком '{self._step_label(self.current_id)}'")
            self.finished.emit()
            return
        self._breakpoint_bypassed = False

        nets = self.model.get_nets(index)
        if nets and self.kicad:
            self.kicad.select_net(*nets, zoomToFit=False)

        self.stepStarted.emit(self.current_id)

        mode = self.model.get_mode(index)

        if mode == "manual":
            # ВАЖЛИВО: waitingUser емітимо ДО _set_state(PAUSED), а не після.
            # UI (MainWindow) слухає stateChanged, щоб миттєво (синхронно)
            # показати текст/колір паузи, і визначає ПРИЧИНУ паузи саме за
            # тим, який з сигналів (waitingUser / breakpointHit / просто
            # pause()) прийшов останнім. Якщо спочатку віддати stateChanged,
            # а вже потім waitingUser — UI встигає намалювати узагальнене
            # "На паузі" ще до того, як дізнається, що це саме ручний крок.
            self.waitingUser.emit(self.current_id)
            self._set_state(DebugState.PAUSED)
            self._status(f"Крок '{self._step_label(self.current_id)}' ручний — очікується дія оператора")
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

        self._advance_from(index, result)
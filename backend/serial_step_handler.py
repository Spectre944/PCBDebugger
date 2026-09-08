from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from PySide6.QtCore import QObject, Signal


DEFAULT_TIMEOUT_MS = 2000
DEFAULT_STEP_DELAY_MS = 500

_PIN_VALUE_RE = re.compile(r"P(\d+)=([01])")


def build_pin_report_table(
    pin_to_net: dict,
    value_rows: dict[int, tuple[int, int | None]] | None = None,
    timeout_pins=(),
    designator: str = "D1",
) -> str:
    """
    Формує HTML-таблицю для логу замість довгого рядка через кому — саме
    ці рядки ("P63(очік.1/факт.0), P64(...), ..." x18) і були
    "нечитаемо" при великих групах пінів. QTextEdit розуміє базовий HTML
    у append(), тому таблиця рендериться як таблиця, а не як текст.

    value_rows: {пін: (очікувано, факт)} — пини з неправильним значенням
                (факт може бути None, якщо пін просто відсутній у кадрі).
    timeout_pins: піни, на яких відповіді не було взагалі (інша причина
                  несправності — обрив зв'язку, а не конкретна лінія).
    """
    value_rows = value_rows or {}
    if not value_rows and not timeout_pins:
        return ""

    rows_html = []
    for pin in sorted(value_rows):
        expected, actual = value_rows[pin]
        net = pin_to_net.get(f"{designator}:{pin}", "-")
        actual_text = str(actual) if actual is not None else "відсутній у відповіді"
        rows_html.append(
            f"<tr><td>P{pin}</td><td>невірне значення</td>"
            f"<td>{expected}</td><td>{actual_text}</td><td>{net}</td></tr>"
        )
    for pin in sorted(timeout_pins):
        net = pin_to_net.get(f"{designator}:{pin}", "-")
        rows_html.append(
            f"<tr><td>P{pin}</td><td>немає відповіді</td>"
            f"<td>—</td><td>—</td><td>{net}</td></tr>"
        )

    return (
        '<table border="1" cellspacing="0" cellpadding="4" '
        'style="border-collapse:collapse; font-family:Consolas,monospace; font-size:12px;">'
        "<tr>"
        "<th>Пін</th><th>Проблема</th><th>Очікувано</th><th>Факт</th><th>Net</th>"
        "</tr>"
        + "".join(rows_html)
        + "</table>"
    )


@dataclass
class PinSweepState:
    """Состояние последовательной проверки группы выводов."""

    pins: list[int]
    set_port: str
    read_port: str
    value: int
    timeout_ms: int

    remaining: list[int] = field(init=False)
    bad_pins: set[int] = field(default_factory=set)
    timeout_pins: set[int] = field(default_factory=set)
    # Пін -> (очікувано, факт) для ПЕРШОГО разу, коли пін виявився поганим —
    # потрібно лише для підсумкової таблиці в кінці обходу, щоб не тягнути
    # повний список на кожній ітерації (це й було головним джерелом шуму).
    mismatch_details: dict[int, tuple[int, int | None]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.remaining = list(self.pins)

    @property
    def total_pins(self) -> int:
        return len(self.pins)

    @property
    def completed(self) -> bool:
        return not self.remaining

    @property
    def failed_pins(self) -> set[int]:
        return self.bad_pins | self.timeout_pins


def build_match_fn(expect: str) -> Callable[[bytes], bytes | None]:
    """
    Создаёт функцию поиска конкретного кадра в буфере.

    Например:

        expect = "$RS TXD READY1*"

    Будет найден именно этот фрагмент, включая конечный '*'.

    Функция не зависит от наличия '\\r\\n' или '\\n' после кадра.
    """

    pattern = expect.encode()

    def match_fn(buffer: bytes) -> bytes | None:
        index = buffer.find(pattern)

        if index == -1:
            return None

        end = index + len(pattern)

        # Возвращаем также данные перед найденным кадром.
        # SerialManager удалит весь этот участок из буфера.
        return bytes(buffer[:end])

    return match_fn


def build_frame_match_fn(prefix: str) -> Callable[[bytes], bytes | None]:
    """
    Создаёт функцию поиска полного кадра с неизвестным содержимым.

    Например:

        "$PORT P63=1,P64=0,...*"

    В этом случае мы заранее не знаем значения выводов,
    поэтому ищем только:

        $PORT ... *

    То есть кадр должен начинаться с указанного prefix
    и заканчиваться символом '*'.
    """

    prefix_bytes = prefix.encode()

    def match_fn(buffer: bytes) -> bytes | None:
        start = buffer.find(prefix_bytes)

        if start == -1:
            return None

        end = buffer.find(b"*", start)

        if end == -1:
            return None

        end += 1

        # Возвращаем всё до конца найденного кадра.
        return bytes(buffer[:end])

    return match_fn


def parse_port_frame(raw: bytes) -> dict[int, int]:
    """
    Разбирает кадр:

        $PORT P63=1,P64=0,P67=1*

    в:

        {
            63: 1,
            64: 0,
            67: 1,
        }
    """

    text = raw.decode(errors="ignore")

    return {
        int(pin): int(value)
        for pin, value in _PIN_VALUE_RE.findall(text)
    }


def get_nets_for_pins(
    pin_numbers: list[int] | set[int],
    pin_to_net: dict[str, str],
    designator: str = "D1",
) -> list[str]:
    """Преобразует номера выводов процессора в имена соответствующих net."""

    nets: list[str] = []

    for pin_number in pin_numbers:
        pin_key = f"{designator}:{pin_number}"
        net_name = pin_to_net.get(pin_key)

        if net_name:
            nets.append(net_name)

    return nets


class SerialStepHandler(QObject):
    """
    Связывает ScenarioRunner с SerialManager.

    ScenarioRunner отвечает за последовательность сценария.

    SerialManager отвечает за:
        - работу с COM-портами;
        - отправку данных;
        - ожидание ответа;
        - таймауты.

    SerialStepHandler связывает эти два уровня и реализует
    логику конкретных автоматических шагов сценария.
    """

    select_bad_nets = Signal(list)

    def __init__(
        self,
        runner,
        serial,
        model,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self.runner = runner
        self.serial = serial
        self.model = model

        self.pin_to_net = self._load_pin_map()

        # Параметры текущего ожидаемого ответа.
        self._active_port: str | None = None
        self._active_verdict: Callable[[bytes], None] | None = None
        self._active_failure_verdict: Callable[[str], None] | None = None

        # Порт, используемый для установки значения PIN
        # во время pin_sweep.
        self._current_set_port: str | None = None

        self._register_handlers()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------

    @staticmethod
    def _load_pin_map() -> dict[str, str]:
        """Загружает соответствие выводов процессора и net."""

        try:
            with open(
                "config\\d1_net_map.json",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(data, dict):
            return {}

        return data

    def _register_handlers(self) -> None:
        """Регистрирует обработчики автоматических шагов."""

        self.runner.register_auto_handler(
            "send_signal",
            self._handle_send_signal,
        )

        self.runner.register_auto_handler(
            "wait_signal",
            self._handle_wait_signal,
        )

        self.runner.register_auto_handler(
            "send_and_wait",
            self._handle_send_and_wait,
        )

        self.runner.register_auto_handler(
            "port_check",
            self._handle_port_check,
        )

        self.runner.register_auto_handler(
            "pin_sweep",
            self._handle_pin_sweep,
        )

    def _connect_signals(self) -> None:
        """Подключает сигналы SerialManager."""

        self.serial.response_received.connect(
            self._on_response
        )

        self.serial.request_failed.connect(
            self._on_failed
        )

    # ------------------------------------------------------------------
    # Простая отправка
    # ------------------------------------------------------------------

    def _handle_send_signal(self, index: int) -> None:
        """Отправляет команду без ожидания ответа."""

        testing = self.model.get_testing(index)

        port_key = testing.get("source", "")
        data = testing.get("send", "")

        if not port_key:
            self.runner.report_result("fail")
            return

        if self.serial.send_signal(
            port_key,
            data.encode(),
        ):
            self.runner.report_result("pass")
            return

        self.runner.report_result("fail")

    # ------------------------------------------------------------------
    # Ожидание сигнала
    # ------------------------------------------------------------------

    def _handle_wait_signal(self, index: int) -> None:
        """Ожидает конкретный кадр без предварительной отправки."""

        testing = self.model.get_testing(index)

        port_key = testing.get("source", "")
        expect = testing.get("expect", "")
        timeout_ms = testing.get(
            "timeout_ms",
            DEFAULT_TIMEOUT_MS,
        )

        if not port_key or not expect:
            self.runner.report_result("fail")
            return

        match_fn = build_match_fn(expect)

        self._set_active_request(
            port_key=port_key,
            success=self._pass_verdict,
            failure=self._fail_verdict,
        )

        self.serial.wait_signal(
            port_key,
            match_fn,
            timeout_ms,
        )

    # ------------------------------------------------------------------
    # Отправка + ожидание
    # ------------------------------------------------------------------

    def _handle_send_and_wait(self, index: int) -> None:
        """Отправляет команду и ожидает конкретный ответ."""

        testing = self.model.get_testing(index)

        port_key = testing.get("source", "")
        send = testing.get("send", "")
        expect = testing.get("expect", "")
        send_suffix = testing.get("send_suffix", "")

        timeout_ms = testing.get(
            "timeout_ms",
            DEFAULT_TIMEOUT_MS,
        )

        if not port_key or not expect:
            self.runner.report_result("fail")
            return

        data = f"{send}{send_suffix}".encode()
        match_fn = build_match_fn(expect)

        self._set_active_request(
            port_key=port_key,
            success=self._pass_verdict,
            failure=self._fail_verdict,
        )

        self.serial.send_and_wait(
            port_key,
            data,
            match_fn,
            timeout_ms,
        )

    # ------------------------------------------------------------------
    # Проверка группы портов
    # ------------------------------------------------------------------

    def _handle_port_check(self, index: int) -> None:
        """
        Отправляет команду опроса портов и проверяет полученный $PORT-кадр.

        Пример:

            send:
                "$ALL TEST OUT*"

            response:
                "$PORT P63=1,P64=0,P67=1*"

            expected:
                {
                    "63": 1,
                    "64": 0,
                    "67": 1,
                }
        """

        testing = self.model.get_testing(index)

        port_key = testing.get("source", "")
        send = testing.get("send", "")
        expected_data = testing.get("expected", {})

        timeout_ms = testing.get(
            "timeout_ms",
            DEFAULT_TIMEOUT_MS,
        )

        if not port_key or not send:
            self.runner.report_result("fail")
            return

        expected = {
            int(pin): int(value)
            for pin, value in expected_data.items()
        }

        # ВАЖНО:
        # Здесь нельзя использовать build_match_fn(), потому что
        # содержимое $PORT заранее неизвестно.
        #
        # Нужно найти кадр вида:
        #
        #     $PORT P63=1,P64=0,...*
        #
        # Поэтому используется структурный matcher.
        match_fn = build_frame_match_fn("$PORT")

        self._set_active_request(
            port_key=port_key,
            success=lambda raw: self._verify_port_frame(
                raw,
                expected,
            ),
            failure=lambda reason: self._port_check_timeout(
                reason,
                send,
                port_key,
            ),
        )

        self.serial.send_and_wait(
            port_key,
            send.encode(),
            match_fn,
            timeout_ms,
        )

    # ------------------------------------------------------------------
    # Последовательная проверка PIN
    # ------------------------------------------------------------------

    def _handle_pin_sweep(self, index: int) -> None:
        """
        Проверяет каждый PIN группы отдельно.

        Для каждого PIN:

        1. На set_port отправляется:

               $PIN P63 1*

        2. На read_port отправляется:

               $ALL TEST OUT*

        3. Ожидается:

               $PORT ...

        4. Полученные значения сравниваются с ожидаемыми.

        Если PIN, отличный от целевого, тоже изменил состояние,
        он считается проблемным.
        """

        testing = self.model.get_testing(index)

        pins = [
            int(pin)
            for pin in testing.get("pins", [])
        ]

        set_port = testing.get("set_port", "")
        read_port = testing.get("read_port", "")

        value = int(testing.get("value", 1))
        timeout_ms = int(
            testing.get(
                "timeout_ms",
                DEFAULT_TIMEOUT_MS,
            )
        )

        if not pins or not set_port or not read_port:
            self.runner.report_result("fail")
            return

        self._current_set_port = set_port

        state = PinSweepState(
            pins=pins,
            set_port=set_port,
            read_port=read_port,
            value=value,
            timeout_ms=timeout_ms,
        )

        self.runner.log_detail(
            f"pin_sweep: перевірка {state.total_pins} "
            f"пінів, цільове значення = {value}"
        )

        self._advance_pin_sweep(state)

    def _advance_pin_sweep(
        self,
        state: PinSweepState,
    ) -> None:
        """Переходит к проверке следующего PIN."""

        if state.completed:
            self._finish_pin_sweep(state)
            return

        pin = state.remaining.pop(0)

        data = f"$PIN P{pin} {state.value}*".encode()

        # Порт для установки значения PIN.
        self._current_set_port = state.set_port

        if not self.serial.send_signal(
            state.set_port,
            data,
        ):
            self.runner.log_detail(
                f"pin_sweep: не вдалося відправити "
                f"команду для P{pin}; "
                f"порт '{state.set_port}' недоступний"
            )

            self.runner.report_result("fail")
            return

        expected = {
            current_pin: (
                state.value
                if current_pin == pin
                else 1 - state.value
            )
            for current_pin in state.pins
        }

        match_fn = build_frame_match_fn("$PORT")

        self._set_active_request(
            port_key=state.read_port,
            success=lambda raw: self._handle_pin_success(
                raw,
                pin,
                expected,
                state,
            ),
            failure=lambda reason: self._handle_pin_failure(
                reason,
                pin,
                state,
            ),
        )

        self.serial.send_and_wait(
            state.read_port,
            b"$ALL TEST OUT*",
            match_fn,
            state.timeout_ms,
        )

    def _handle_pin_success(
        self,
        raw: bytes,
        pin: int,
        expected: dict[int, int],
        state: PinSweepState,
    ) -> None:
        """Обрабатывает ответ на проверку одного PIN."""

        actual = parse_port_frame(raw)

        mismatches = {
            current_pin: (
                expected_value,
                actual.get(current_pin),
            )
            for current_pin, expected_value in expected.items()
            if actual.get(current_pin) != expected_value
        }

        if mismatches:
            state.bad_pins.update(mismatches)
            for current_pin, pair in mismatches.items():
                # Тримаємо лише ПЕРШИЙ випадок кожного піна — для звіту в
                # кінці досить одного прикладу "чому саме він поганий";
                # значення все одно майже завжди однакові на кожній ітерації.
                state.mismatch_details.setdefault(current_pin, pair)

            # ВИПРАВЛЕНО (нечитаемость): раніше тут друкувався повний
            # список всіх розбіжностей (до 18 пінів в один рядок) — і так
            # на КОЖНІЙ з N ітерацій, тобто та сама простиня повторювалась
            # N разів майже без змін. Тепер лише короткий підсумок за
            # ітерацію; повна таблиця — один раз, в кінці обходу.
            # self.runner.log_detail( f"PIN_SWEEP: ціль P{pin}={state.value} — розбіжність ({len(mismatches)} пінів, деталі в підсумку)" )
        self._advance_pin_sweep(state)

    def _handle_pin_failure(
        self,
        reason: str,
        pin: int,
        state: PinSweepState,
    ) -> None:
        """Обрабатывает отсутствие ответа на проверку PIN."""

        state.timeout_pins.add(pin)

        self.runner.log_detail(
            f"PIN_SWEEP: ціль P{pin}={state.value} — "
            f"немає відповіді від плати "
            f"(timeout, {reason})"
        )

        self._advance_pin_sweep(state)

    def _finish_pin_sweep(
        self,
        state: PinSweepState,
    ) -> None:
        """Завершает проверку группы PIN."""

        failed_pins = state.failed_pins

        self._current_set_port = None

        if not failed_pins:
            self.runner.log_detail( f"PIN_SWEEP: усі {state.total_pins} пінів пройшли перевірку" )
            self.runner.report_result("pass")
            return

        self.runner.log_detail(
            f"PIN_SWEEP: проблемні лінії ({len(failed_pins)} з {state.total_pins})"
        )
        self.runner.log_detail(
            build_pin_report_table(
                self.pin_to_net,
                state.mismatch_details,
                state.timeout_pins,
            )
        )

        bad_nets = get_nets_for_pins(
            failed_pins,
            self.pin_to_net,
        )

        if bad_nets:
            self.select_bad_nets.emit(bad_nets)

        self.runner.report_result("fail")

    # ------------------------------------------------------------------
    # Вердикты
    # ------------------------------------------------------------------

    def _pass_verdict(self, raw: bytes) -> None:
        """Успешный ответ."""

        self.runner.report_result("pass")

    def _fail_verdict(self, reason: str) -> None:
        """Стандартная ошибка ожидания."""

        self.runner.report_result("fail")

    def _port_check_timeout(
        self,
        reason: str,
        send: str,
        port_key: str,
    ) -> None:
        """Обрабатывает отсутствие ответа при проверке портов."""

        self.runner.log_detail(
            f"port_check: немає відповіді на '{send}' "
            f"з порту '{port_key}' "
            f"(timeout, {reason})"
        )

        self.runner.report_result("fail")

    def _verify_port_frame(
        self,
        raw: bytes,
        expected: dict[int, int],
    ) -> None:
        """Проверяет значения PIN в полученном $PORT-кадре."""

        actual = parse_port_frame(raw)

        mismatches = {
            pin: (
                expected_value,
                actual.get(pin),
            )
            for pin, expected_value in expected.items()
            if actual.get(pin) != expected_value
        }

        if not mismatches:
            self.runner.report_result("pass")
            return

        self.runner.log_detail(
            f"PORT_CHECK: розбіжність ({len(mismatches)} з {len(expected)} пінів)"
        )
        self.runner.log_detail(
            build_pin_report_table(self.pin_to_net, mismatches)
        )

        bad_nets = get_nets_for_pins(
            mismatches.keys(),
            self.pin_to_net,
        )

        if bad_nets:
            self.select_bad_nets.emit(bad_nets)

        self.runner.report_result("fail")

    # ------------------------------------------------------------------
    # Управление активным запросом
    # ------------------------------------------------------------------

    def _set_active_request(
        self,
        port_key: str,
        success: Callable[[bytes], None],
        failure: Callable[[str], None],
    ) -> None:
        """Устанавливает обработчики текущего ожидаемого ответа."""

        self._active_port = port_key
        self._active_verdict = success
        self._active_failure_verdict = failure

    def _clear_active_request(self) -> None:
        """Очищает состояние текущего ожидаемого ответа."""

        self._active_port = None
        self._active_verdict = None
        self._active_failure_verdict = None

    # ------------------------------------------------------------------
    # SerialManager callbacks
    # ------------------------------------------------------------------

    def _on_response(
        self,
        port_key: str,
        matched_data: bytes,
    ) -> None:
        """
        Обрабатывает успешно найденный ответ.

        Ответ с другого порта игнорируется.
        """

        if port_key != self._active_port:
            return

        verdict = self._active_verdict

        self._clear_active_request()

        if verdict is not None:
            verdict(matched_data)

    def _on_failed(
        self,
        port_key: str,
        reason: str,
    ) -> None:
        """Обрабатывает timeout или ошибку SerialManager."""

        if port_key != self._active_port:
            return

        verdict = self._active_failure_verdict

        self._clear_active_request()

        if verdict is not None:
            verdict(reason)
            return

        self.runner.report_result("fail")
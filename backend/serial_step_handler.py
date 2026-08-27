"""
Місток між ScenarioRunner і SerialManager для авто-кроків сценарію.

ScenarioRunner нічого не знає про формат даних на шинах — він лише викликає
зареєстрований handler(index) для testing.kind і чекає report_result().
SerialManager нічого не знає про сценарій — йому потрібні port_key, дані і
match_fn, і саме він вирішує pass/fail на рівні "прийшов пакет / таймаут".

SerialStepHandler зшиває їх:
  - дістає з testing (mode="auto") потрібні поля (expect/send/timeout_ms);
  - визначає порт та будує match_fn;
  - викликає serial.wait_signal / serial.send_and_wait;
  - слухає відповіді serial і зіставляє їх з активним запитом раннера
    (за port_key), після чого викликає runner.report_result("pass"/"fail").

Формат testing (scenario.json), приклад:
    "testing": {
        "mode": "auto",
        "kind": "wait_signal",
        "expect": "$RS TXD READY2*"
    }

ВАЖЛИВО (виправлено після тесту з "$RS TXD READY1*", який не спрацював):
рядки протоколу мають вигляд рамки "$...*" — '$' це початок кадру, а '*' це
його СПРАВЖНІЙ кінець (як у NMEA), а не wildcard і не роздільник рядків.
Попередня версія різала буфер по b"\\r\\n" і трактувала кінцевий '*' як
wildcard — якщо пристрій не шле \\r\\n (або шле \\r чи \\n окремо), кінець
пакету просто ніколи не знаходився і перевірка завжди йшла в timeout,
незалежно від того, що саме прийшло. Тепер шукаємо весь рядок expect
ЦІЛИКОМ (разом з кінцевим '*') як підрядок у буфері — без будь-яких
припущень про переведення рядка.

Порт визначається за першим токеном рядка expect/send: "$RS" -> port_key
"RS", "$BT" -> port_key "BT" — ті самі ключі, якими порти реєструються в
SerialManager.add_port("RS", ...) / add_port("BT", ...). Якщо насправді
порт кроку задається окремим полем — замініть _extract_port_key() на
testing.get("port").
"""

from PySide6.QtCore import QObject


DEFAULT_TIMEOUT_MS = 2000


def _extract_port_key(pattern: str) -> str:
    """'$RS TXD READY2*' -> 'RS'"""
    if not pattern:
        return ""
    token = pattern.split()[0]
    return token.lstrip("$")


def build_match_fn(expect: str):
    """
    Пакет — рамка "$...*". Шукаємо рядок expect ЦІЛИКОМ (включно з кінцевим
    '*') як підрядок у буфері. Це працює незалежно від того, чим саме
    термінується потік байтів навколо кадру (\\r\\n, \\n, нічим і т.д.),
    і не вимагає жодних припущень про wildcard.
    """
    pattern = expect.encode()

    def match_fn(buffer: bytes):
        idx = buffer.find(pattern)
        if idx == -1:
            return None  # кадр ще не прийшов повністю (або не прийшов взагалі)
        end = idx + len(pattern)
        # "з'їдаємо" все включно з початком кадру — сміття перед ним теж
        # відкидаємо, щоб не заважало наступному очікуванню.
        return bytes(buffer[:end])

    return match_fn


class SerialStepHandler(QObject):
    """Зв'язує ScenarioRunner і SerialManager для узгодження запит/відповідь."""

    def __init__(self, runner, serial, model, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.serial = serial
        self.model = model

        # Порт, на якому зараз очікується відповідь для активного кроку.
        # Потрібен, щоб "чужа"/запізніла відповідь не закрила не свій крок.
        self._active_port = None

        runner.register_auto_handler("wait_signal", self._handle_wait_signal)
        runner.register_auto_handler("send_and_wait", self._handle_send_and_wait)

        self.serial.responseReceived.connect(self._on_response)
        self.serial.requestFailed.connect(self._on_failed)

    # ---- Обробники auto-кроків, викликаються ScenarioRunner ----

    def _handle_wait_signal(self, index):
        testing = self.model.get_testing(index)
        expect = testing.get("expect", "")
        timeout_ms = testing.get("timeout_ms", DEFAULT_TIMEOUT_MS)

        port_key = _extract_port_key(expect)
        match_fn = build_match_fn(expect)

        self._active_port = port_key
        self.serial.wait_signal(port_key, match_fn, timeout_ms)

    def _handle_send_and_wait(self, index):
        testing = self.model.get_testing(index)
        send = testing.get("send", "")
        expect = testing.get("expect", "")
        timeout_ms = testing.get("timeout_ms", DEFAULT_TIMEOUT_MS)
        # Якщо кадр не самотермінований (без кінцевого '*') — можна задати
        # в testing.json "send_suffix": "\r\n". За замовчуванням нічого не
        # дописуємо, бо кадр "$...*" вже сам собі термінатор.
        send_suffix = testing.get("send_suffix", "")

        port_key = _extract_port_key(send) or _extract_port_key(expect)
        match_fn = build_match_fn(expect)
        data = (send + send_suffix).encode()

        self._active_port = port_key
        self.serial.send_and_wait(port_key, data, match_fn, timeout_ms)

    # ---- Відповіді від SerialManager ----

    def _on_response(self, port_key, matched_data):
        if port_key != self._active_port:
            return  # відповідь прийшла не по активному запиту — ігноруємо
        self._active_port = None
        self.runner.report_result("pass")

    def _on_failed(self, port_key, reason):
        if port_key != self._active_port:
            return
        self._active_port = None
        self.runner.report_result("fail")
from functools import wraps

from PySide6.QtCore import QObject, QTimer, Signal
from kipy import KiCad


CONNECTION_ERROR = "Помилка: Не вдалося з'єднатися з KiCad"
NOT_CONNECTED = "Помилка: Відсутнє з'єднання з KiCad"
CONNECTION_LOST = "Помилка: З'єднання з KiCad втрачено"
CONNECTION_SUCCESS = "Інфо: З'єднано з KiCad"
CONNECTION_PROGRESS = "Інфо: Підключення до KiCad… спроба {attempt}/{total}"

ZOOM_TO_SELECTION_ACTION = "common.Control.zoomFitSelection"


def _ipc_call(method):
    """
    Decorator for methods that talk to KiCad.

    - skips the call if there is no connection (no IPC timeout wait);
    - if the call fails (KiCad closed, socket dead), drops the connection,
      so following calls are skipped instantly instead of lagging.
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self._check_connection():
            return None

        try:
            return method(self, *args, **kwargs)
        except Exception as exc:
            self._on_connection_lost(exc)
            return None

    return wrapper



class KiCadApi(QObject):
    """Interface for communication with KiCad via IPC API."""

    connection_status_changed = Signal(str)
    connection_error = Signal(str, str)
    selected_nets_changed = Signal(list)

    # Connection retry settings: 10 attempts * 3 s ~= 30 s
    CONNECT_INTERVAL_MS = 3000
    CONNECT_MAX_ATTEMPTS = 10
    # Timeout of a single IPC request, so the UI is not blocked for long
    IPC_TIMEOUT_MS = 1000

    def __init__(self, parent=None, kicad_process=None):
        """
        Args:
            parent: Qt parent.
            kicad_process: Optional subprocess.Popen of the launched KiCad.
                If it exits while we are waiting, retries stop immediately.
        """
        super().__init__(parent)

        self.kicad_process = kicad_process

        self.kicad = None
        self.board = None
        self.nets = None
        self.footprints = None
        self.settings = None

        self._attempt = 0
        self._last_error = ("", "")

        self._connect_timer = QTimer(self)
        self._connect_timer.setInterval(self.CONNECT_INTERVAL_MS)
        self._connect_timer.timeout.connect(self._on_connect_tick)

    # -------------------------------------------------------------------------
    # Connection
    # -------------------------------------------------------------------------

    def connect(self) -> None:
        """
        Start connecting to KiCad with retries.

        Does not block: the first attempt is made immediately, then the timer
        repeats it until success or until CONNECT_MAX_ATTEMPTS is exhausted.
        Result is reported via signals:
            - connection_status_changed (progress / success / failure)
            - connection_error (only once, after all attempts failed)
        """

        self.cancel_connect()
        self.disconnect()

        # The process we launched earlier may already be closed (user closed
        # KiCad and opened it manually). It is stale, so stop watching it,
        # otherwise we would fail with "process exited (code 0)".
        if self.kicad_process is not None and self.kicad_process.poll() is not None:
            self.kicad_process = None

        self._attempt = 0
        self._last_error = ("", "")

        self._on_connect_tick()  # first attempt right away

        # Tick may have already finished (success / fatal error)
        if self._attempt < self.CONNECT_MAX_ATTEMPTS and not self.is_connected():
            if not self._finished_with_error:
                self._connect_timer.start()

    def reconnect(self) -> None:
        """Reconnect to KiCad."""

        self.connect()

    def cancel_connect(self) -> None:
        """Stop pending connection attempts."""

        self._connect_timer.stop()

    def is_connecting(self) -> bool:
        """Return True while retry timer is running."""

        return self._connect_timer.isActive()

    def disconnect(self) -> None:
        """Reset the current KiCad connection."""

        self.kicad = None
        self.board = None
        self.nets = None
        self.footprints = None
        self.settings = None

    def is_connected(self) -> bool:
        """Return True if KiCad and a board are available."""

        return self.kicad is not None and self.board is not None

    # -------------------------------------------------------------------------
    # Connection internals
    # -------------------------------------------------------------------------

    _finished_with_error = False

    def _on_connect_tick(self) -> None:
        """One step of the retry loop."""

        self._finished_with_error = False

        # KiCad was closed/crashed while we were waiting - no reason to wait on
        if self.kicad_process is not None and self.kicad_process.poll() is not None:
            self._fail(
                "KiCad завершився",
                (
                    "Процес KiCad завершився до того, як вдалося підключитися "
                    f"(код {self.kicad_process.returncode})."
                ),
            )
            return

        self._attempt += 1
        self.connection_status_changed.emit(
            CONNECTION_PROGRESS.format(
                attempt=self._attempt,
                total=self.CONNECT_MAX_ATTEMPTS,
            )
        )

        if self._try_connect():
            self._connect_timer.stop()
            self.connection_status_changed.emit(CONNECTION_SUCCESS)
            return

        if self._attempt >= self.CONNECT_MAX_ATTEMPTS:
            title, message = self._last_error
            self._fail(title, message)

    def _try_connect(self) -> bool:
        """
        Single connection attempt. Never shows dialogs or emits errors;
        the reason of failure is stored in self._last_error.
        """

        self.disconnect()

        try:
            self.kicad = KiCad(timeout_ms=self.IPC_TIMEOUT_MS)
        except Exception as exc:
            self.disconnect()
            self._last_error = (
                "KiCad не запущено",
                (
                    "Не вдалося підключитися до KiCad.\n\n"
                    "Перевірте, що:\n"
                    "• KiCad запущено\n"
                    "• У налаштуваннях KiCad увімкнено IPC API "
                    "(Налаштування → Плагіни та API)\n\n"
                    f"Деталі: {exc}"
                ),
            )
            return False

        try:
            board = self.kicad.get_board()
            nets = board.get_nets()
            footprints = board.get_footprints()
            settings = board.get_editor_appearance_settings()

            if len(nets) <= 1 and not footprints:
                raise RuntimeError("Плата порожня або не відкрита")

            self.board = board
            self.nets = nets
            self.footprints = footprints
            self.settings = settings

            self._configure_board()

        except Exception as exc:
            self.disconnect()
            self._last_error = (
                "Проєкт не відкрито",
                (
                    "KiCad запущено, але не вдалося отримати доступ до плати.\n\n"
                    "Перевірте, що в KiCad відкрито проєкт/плату "
                    "(PCB Editor).\n\n"
                    f"Деталі: {exc}"
                ),
            )
            return False

        return True

    def _fail(self, title: str, message: str) -> None:
        """Stop retries and notify listeners about the final failure."""

        self._connect_timer.stop()
        self._finished_with_error = True
        self._handle_connection_error(title, message)

    # -------------------------------------------------------------------------
    # Board
    # -------------------------------------------------------------------------

    def _configure_board(self) -> None:
        """Apply required appearance settings to the current board."""

        self.settings.net_color_display = 0 # or 1 (brighter color)
        self.board.set_editor_appearance_settings(self.settings)

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    @_ipc_call
    def clear_selection(self) -> None:
        """Clear the current selection in KiCad."""

        self.board.clear_selection()

    @_ipc_call
    def select_net(
        self,
        *net_names: str,
        zoom_to_fit: bool = False,
    ) -> None:
        """
        Select all items belonging to the specified nets.

        Args:
            *net_names: Names of the nets to select.
            zoom_to_fit: Zoom the view to the selected items.
        """

        self.board.clear_selection()

        selected_nets = []
        total_items = 0

        for net_name in net_names:
            net = self._find_net(net_name)

            if net is None:
                continue

            items = self.board.get_items_by_net(net)

            if not items:
                continue

            self.board.add_to_selection(items)

            selected_nets.append(net_name)
            total_items += len(items)

        self.selected_nets_changed.emit(selected_nets)

        if zoom_to_fit and total_items:
            self._zoom_to_selection()

    @_ipc_call
    def select_net_pins(
        self,
        *net_names: str,
        zoom_to_fit: bool = False,
    ) -> None:
        """
        Select all pads belonging to the specified nets.

        Args:
            *net_names: Names of the nets whose pads should be selected.
            zoom_to_fit: Zoom the view to the selected pads.
        """

        net_names = set(net_names)
        matched_pads = []

        for footprint in self.footprints:
            for pad in footprint.definition.pads:
                if pad.net and pad.net.name in net_names:
                    matched_pads.append(pad)

        if not matched_pads:
            return

        self.board.clear_selection()
        self.board.add_to_selection(matched_pads)

        if zoom_to_fit:
            self._zoom_to_selection()

    @_ipc_call
    def select_footprint_pins(
        self,
        *footprint_names: str,
        zoom_to_fit: bool = False,
    ) -> None:
        """
        Select all pads belonging to the specified footprints.

        Args:
            *footprint_names: References of the footprints.
            zoom_to_fit: Zoom the view to the selected pads.
        """

        footprint_names = set(footprint_names)
        matched_pads = []

        for footprint in self.footprints:
            name = footprint.reference_field.text.value

            if name in footprint_names:
                matched_pads.extend(footprint.definition.pads)

        if not matched_pads:
            return

        self.board.clear_selection()
        self.board.add_to_selection(matched_pads)

        if zoom_to_fit:
            self._zoom_to_selection()

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _check_connection(self) -> bool:
        """Check whether the API is connected to KiCad."""

        if not self.is_connected():
            self.connection_status_changed.emit(NOT_CONNECTED)
            return False

        # KiCad was closed: detect it instantly, without waiting for IPC timeout
        if self.kicad_process is not None and self.kicad_process.poll() is not None:
            self._on_connection_lost("процес KiCad завершився")
            return False

        return True

    def _on_connection_lost(self, reason) -> None:
        """Drop the dead connection and notify listeners once."""

        was_connected = self.is_connected()
        self.disconnect()

        if was_connected:
            self.connection_status_changed.emit(CONNECTION_LOST)

    def _find_net(self, net_name: str):
        """Find a net by its name."""

        return next(
            (net for net in self.nets if net.name == net_name),
            None,
        )

    def _zoom_to_selection(self) -> None:
        """Zoom KiCad view to the current selection."""

        self.kicad.run_action(ZOOM_TO_SELECTION_ACTION)

    def _handle_connection_error(
        self,
        title: str,
        message: str,
    ) -> None:
        """Reset connection and notify listeners about an error."""

        self.disconnect()

        self.connection_error.emit(title, message)
        self.connection_status_changed.emit(CONNECTION_ERROR)
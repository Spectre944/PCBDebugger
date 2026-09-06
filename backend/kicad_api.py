from PySide6.QtCore import QObject, Signal
from kipy import KiCad


CONNECTION_ERROR = "Помилка: Не вдалося з'єднатися з KiCad"
NOT_CONNECTED = "Помилка: Відсутнє з'єднання з KiCad"
CONNECTION_SUCCESS = "Інфо: З'єднано з KiCad"

ZOOM_TO_SELECTION_ACTION = "common.Control.zoomFitSelection"


class KiCadApi(QObject):
    """Interface for communication with KiCad via IPC API."""

    connection_status_changed = Signal(str)
    connection_error = Signal(str, str)
    selected_nets_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.kicad = None
        self.board = None
        self.nets = None
        self.footprints = None
        self.settings = None

    # -------------------------------------------------------------------------
    # Connection
    # -------------------------------------------------------------------------

    def connect(self) -> bool:
        """Connect to KiCad and initialize the current board."""

        self.disconnect()

        try:
            self.kicad = KiCad()
        except Exception as exc:
            self._handle_connection_error(
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
            self.board = self.kicad.get_board()
            self.nets = self.board.get_nets()
            self.footprints = self.board.get_footprints()
            self.settings = self.board.get_editor_appearance_settings()

            self._configure_board()

            if len(self.nets) <= 1 and not self.footprints:
                raise RuntimeError("Плата порожня або не відкрита")

        except Exception as exc:
            self._handle_connection_error(
                "Проєкт не відкрито",
                (
                    "KiCad запущено, але не вдалося отримати доступ до плати.\n\n"
                    "Перевірте, що в KiCad відкрито проєкт/плату "
                    "(PCB Editor).\n\n"
                    f"Деталі: {exc}"
                ),
            )
            return False

        self.connection_status_changed.emit(CONNECTION_SUCCESS)
        return True

    def reconnect(self) -> bool:
        """Reconnect to KiCad."""

        return self.connect()

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
    # Board
    # -------------------------------------------------------------------------

    def _configure_board(self) -> None:
        """Apply required appearance settings to the current board."""

        self.settings.net_color_display = 0 # or 1 (brighter color)
        self.board.set_editor_appearance_settings(self.settings)

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def clear_selection(self) -> None:
        """Clear the current selection in KiCad."""

        if not self._check_connection():
            return

        self.board.clear_selection()

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

        if not self._check_connection():
            return

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

        if not self._check_connection():
            return

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

        if not self._check_connection():
            return

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

        if self.is_connected():
            return True

        self.connection_status_changed.emit(NOT_CONNECTED)
        return False

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
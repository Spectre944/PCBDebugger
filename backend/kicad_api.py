from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal
from kipy import KiCad


class KiCAD_API(QObject):

    connection_status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.kicad = None
        self.board = None
        self.nets = None
        self.footprints = None

        self.connect()

    def connect(self, parent=None) -> bool:
        try:
            self.kicad = KiCad()
        except Exception as e:
            self._show_error(
                parent,
                "KiCad не запущено",
                "Не вдалося підключитися до KiCad.\n\n"
                "Перевірте, що:\n"
                "• KiCad запущено\n"
                "• У налаштуваннях KiCad увімкнено IPC API "
                "(Налаштування → Плагіни та API)\n\n"
                f"Деталі: {e}"
            )
            self.disconnect()
            self.connection_status_changed.emit("Не владося з'єднатись з KiCad")
            return False

        try:
            self.board = self.kicad.get_board()
            self.nets = self.board.get_nets()
            self.footprints = self.board.get_footprints()

            # Эвристика: если нет ни цепей, ни footprint'ов — считаем, что проект не открыт
            if len(self.nets) <= 1 and not self.footprints:
                raise RuntimeError("Плата порожня або не відкрита")

        except Exception as e:
            self._show_error(
                parent,
                "Проєкт не відкрито",
                "KiCad запущено, але не вдалося отримати доступ до плати.\n\n"
                "Перевірте, що в KiCad відкрито проєкт/плату (PCB Editor).\n\n"
                f"Деталі: {e}"
            )
            self.disconnect()
            self.connection_status_changed.emit("Не владося з'єднатись з KiCad")
            return False

        self.connection_status_changed.emit("З'єднано з KiCad")
        return True

    def reconnect(self, parent=None) -> bool:
        self.disconnect()
        return self.connect(parent=parent)

    def disconnect(self):
        self.kicad = None
        self.board = None
        self.nets = None
        self.footprints = None

    def is_connected(self) -> bool:
        return self.kicad is not None and self.board is not None

    @staticmethod
    def _show_error(parent, title, text):
        QMessageBox.critical(parent, title, text)

    def clear_selection(self):
        self.board.clear_selection()

    def select_net(self, *net_names, zoomToFit=False):
        self.board.clear_selection()
        total = 0

        for net_name in net_names:
            target_net = next((n for n in self.nets if n.name == net_name), None)
            if target_net is None:
                print(f"Net '{net_name}' не знайдена")
                continue

            items = self.board.get_items_by_net(target_net)
            self.board.add_to_selection(items)
            total += len(items)

        print(f"Обрано {total} обєктів для мереж: {', '.join(net_names)}")

        if zoomToFit:
            self.kicad.run_action("common.Control.zoomFitSelection")

    def select_net_pins(self, *net_names, zoomToFit=False):
        matched_pads = []

        for fp in self.footprints:
            for pad in fp.definition.pads:
                if pad.net.name in net_names:
                    matched_pads.append(pad)

        if not matched_pads:
            print(f"Піни net {', '.join(net_names)} не знайдені")
            return

        self.board.clear_selection()
        self.board.add_to_selection(matched_pads)
        print(f"Обрано {len(matched_pads)} пінів для net: {', '.join(net_names)}")

        if zoomToFit:
            self.kicad.run_action("common.Control.zoomFitSelection")

    def select_footprint_pins(self, *footprint_names, zoomToFit=False):
        matched_pads = []
        matched_footprints = []

        for fp in self.footprints:
            fp_name = fp.reference_field.text.value

            if fp_name in footprint_names:
                matched_footprints.append(fp_name)
                matched_pads.extend(fp.definition.pads)

        if not matched_pads:
            print(f"Футпринти {', '.join(footprint_names)} не знайдені")
            return

        self.board.clear_selection()
        self.board.add_to_selection(matched_pads)
        print(f"Обрано {len(matched_pads)} пінів для футпринтів: {', '.join(matched_footprints)}")

        if zoomToFit:
            self.kicad.run_action("common.Control.zoomFitSelection")

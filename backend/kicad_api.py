from kipy import KiCad

class KiCAD_API():
    def __init__(self):
        self.kicad = None
        self.board = None
        self.nets = None
        self.footprints = None

        self.connect()

    def connect(self):
        self.kicad = KiCad()

        self.board = self.kicad.get_board()
        self.nets = self.board.get_nets()
        self.footprints = self.board.get_footprints()
        


    def clear_selection(self):
        self.board.clear_selection()

    def select_net(self, net_name, zoomToFit = False):
        target_net = next((n for n in self.nets if n.name == net_name), None)

        if target_net is None:
            print(f"Сеть '{net_name}' не найдена")
        else:
            items = self.board.get_items_by_net(target_net)
            self.board.clear_selection()
            self.board.add_to_selection(items)   # именно на этом выделении и будет построен зум
            print(f"Выделено и приближено {len(items)} объектов сети '{net_name}'")

        if zoomToFit is True:
            self.kicad.run_action("common.Control.zoomFitSelection")

    def select_net_pins(self, net_name, zoomToFit=False):
        matched_pads = []

        for fp in self.footprints:
            for pad in fp.definition.pads:
                if pad.net.name == net_name:
                    matched_pads.append(pad)

        if not matched_pads:
            print(f"Пины сети '{net_name}' не найдены")
            return

        self.board.clear_selection()
        self.board.add_to_selection(matched_pads)
        print(f"Выделено {len(matched_pads)} пинов сети '{net_name}'")

        if zoomToFit:
            self.kicad.run_action("common.Control.zoomFitSelection")

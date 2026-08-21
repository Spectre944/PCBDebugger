from kipy import KiCad

kicad = KiCad()
board = kicad.get_board()

net_name = "ZAH_VP1"
nets = board.get_nets()
target_net = next((n for n in nets if n.name == net_name), None)

if target_net is None:
    print(f"Сеть '{net_name}' не найдена")
else:
    items = board.get_items_by_net(target_net)

    board.clear_selection()
    board.add_to_selection(items)   # именно на этом выделении и будет построен зум

    kicad.run_action("common.Control.zoomFitSelection")

    print(f"Выделено и приближено {len(items)} объектов сети '{net_name}'")
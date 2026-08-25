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

'''
ref_name = "X1"
pin_number = "1"

footprints = board.get_footprints()
target_fp = next((fp for fp in footprints if fp.reference_field.text.value == ref_name), None)

if target_fp is None:
    print(f"Футпринт '{ref_name}' не найден")
else:
    target_pad = next((p for p in target_fp.definition.pads if p.number == pin_number), None)
    if target_pad is None:
        print(f"Пин '{pin_number}' не найден на футпринте '{ref_name}'")
    else:
        board.clear_selection()
        board.add_to_selection([target_pad])
        kicad.run_action("common.Control.zoomFitSelection")
        print(f"Выделен пин {ref_name}.{pin_number}")
'''
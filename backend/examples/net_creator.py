import json
from kipy import KiCad

kicad = KiCad()
board = kicad.get_board()



def create_all_net_map():
    net_map = {}

    for fp in board.get_footprints():
        ref = fp.reference_field.text.value
        for pad in fp.definition.pads:
            net_name = pad.net.name
            if not net_name:
                continue  # пад без назначенной сети

            pin_id = f"{ref}:{pad.number}"

            if net_name not in net_map:
                net_map[net_name] = {
                    "pins": [],
                    "description": ""
                }
            net_map[net_name]["pins"].append(pin_id)

    # сортируем пины внутри каждой сети для стабильного вывода
    for net in net_map.values():
        net["pins"].sort()

    with open("config/net_map.json", "w", encoding="utf-8") as f:
        json.dump(net_map, f, ensure_ascii=False, indent=4)

    print(f"Сохранено {len(net_map)} сетей в net_map.json")

def create_d1_net_map():
    net_map = {}

    # Ищем футпринт с обозначением D1
    target_footprint = None
    for fp in board.get_footprints():
        ref = fp.reference_field.text.value
        if ref == "D1":
            target_footprint = fp
            break

    if target_footprint is None:
        print("Футпринт D1 не найден!")
        exit(1)

    # Обрабатываем только найденный футпринт
    ref = target_footprint.reference_field.text.value
    for pad in target_footprint.definition.pads:
        net_name = pad.net.name
        if not net_name:
            continue  # пад без назначенной сети

        pin_id = f"{ref}:{pad.number}"

        if net_name not in net_map:
            net_map[net_name] = {
                "pins": []
            }
        net_map[net_name]["pins"].append(pin_id)

    # сортируем пины внутри каждой сети для стабильного вывода
    for net in net_map.values():
        net["pins"].sort()

    with open("config/d1_net_map.json", "w", encoding="utf-8") as f:
        json.dump(net_map, f, ensure_ascii=False, indent=4)

    print(f"Сохранено {len(net_map)} сетей для футпринта D1 в d1_net_map.json")

import json

def create_d1_net_map_pad_first():
    """
    Создает карту сетей для футпринта D1 в формате pin:net
    """
    net_map = {}

    # Ищем футпринт с обозначением D1
    target_footprint = None
    for fp in board.get_footprints():
        ref = fp.reference_field.text.value
        if ref == "D1":
            target_footprint = fp
            break

    if target_footprint is None:
        print("Футпринт D1 не найден!")
        return None

    # Обрабатываем только найденный футпринт
    ref = target_footprint.reference_field.text.value
    
    for pad in target_footprint.definition.pads:
        net_name = pad.net.name
        if not net_name:
            continue  # пад без назначенной сети

        pin_id = f"{ref}:{pad.number}"
        
        # Формат: pin : net
        net_map[pin_id] = net_name

    # Сортируем по номеру пина для стабильного вывода
    sorted_net_map = {}
    for pin_id in sorted(net_map.keys(), key=lambda x: int(x.split(':')[1])):
        sorted_net_map[pin_id] = net_map[pin_id]

    # Сохраняем в JSON
    with open("config/d1_net_map.json", "w", encoding="utf-8") as f:
        json.dump(sorted_net_map, f, ensure_ascii=False, indent=4)

    print(f"Сохранено {len(sorted_net_map)} пинов для футпринта D1 в d1_net_map.json")
    
    return sorted_net_map

#####################


create_d1_net_map_pad_first()

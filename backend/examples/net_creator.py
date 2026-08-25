import json
from kipy import KiCad

kicad = KiCad()
board = kicad.get_board()

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
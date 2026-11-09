import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path


DEFAULT_PORT_SETTINGS = {
    "port_name": "COM1",
    "baudrate": 19200,
    "stop_bit": "1",
    "parity": "None",
    "flow_control": "None",
    "auto_connect": False,   # reconnect to this port on the next program start
}

# Значения по умолчанию для конкретных портов (перекрывают общие)
PORT_DEFAULTS = {
    "RS": {"port_name": "COM20"},
    "BT": {"port_name": "COM21"},
}


class AppSettings:
    """
    Application settings stored in a JSON file.

    File layout::

        {
          "ports": {
            "BT": {"port_name": "COM21", "baudrate": 19200, "stop_bit": "1",
                   "parity": "None", "flow_control": "None",
                   "auto_connect": true},
            "RS": {...}
          }
        }

    A missing or damaged file is not an error: defaults are used and the
    file is created on the first save.
    """

    def __init__(self, path: str | os.PathLike = "config/settings.json"):
        self.path = Path(path)
        self._data: dict = {"ports": {}}
        self.load()

    # -------------------------------------------------------------------------
    # File
    # -------------------------------------------------------------------------

    def load(self) -> None:
        """Load settings from disk."""

        self._data = {"ports": {}}

        if not self.path.exists():
            return

        try:
            with open(self.path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError("root must be an object")
        except (OSError, ValueError):
            # Битый файл: сохраняем копию, чтобы не потерять данные пользователя
            self._backup_broken_file()
            return

        self._data.update(data)

        if not isinstance(self._data.get("ports"), dict):
            self._data["ports"] = {}

    def save(self) -> None:
        """Write settings atomically (temp file + replace)."""

        self.path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=self.path.parent, prefix=self.path.name, suffix=".tmp"
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(self._data, file, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        except OSError:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _backup_broken_file(self) -> None:
        try:
            os.replace(self.path, self.path.with_suffix(".json.bad"))
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # Ports
    # -------------------------------------------------------------------------

    def get_port(self, port_key: str) -> dict:
        """Return port settings merged with defaults (always complete)."""

        result = deepcopy(DEFAULT_PORT_SETTINGS)
        result.update(PORT_DEFAULTS.get(port_key, {}))

        saved = self._data["ports"].get(port_key)

        if isinstance(saved, dict):
            for key in result:
                if key in saved:
                    result[key] = saved[key]

        try:
            result["baudrate"] = int(result["baudrate"])
        except (TypeError, ValueError):
            result["baudrate"] = DEFAULT_PORT_SETTINGS["baudrate"]

        result["auto_connect"] = bool(result["auto_connect"])

        for key in ("port_name", "stop_bit", "parity", "flow_control"):
            result[key] = str(result[key])

        return result

    def update_port(self, port_key: str, **values) -> None:
        """Change some port settings and save the file."""

        port = self.get_port(port_key)

        for key, value in values.items():
            if key in port:
                port[key] = value

        self._data["ports"][port_key] = port

        try:
            self.save()
        except OSError:
            # Нет прав на запись и т.п.: настройки просто не сохранятся,
            # программа при этом продолжает работать.
            pass

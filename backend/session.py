import json

from backend.models.list_model import TaskListModel, TaskStatus


class DiagnosticSession:
    """Сохранение/загрузка прогресса диагностики поверх существующей модели."""

    def __init__(self, model: TaskListModel):
        self.model = model
        self.log_lines: list[str] = []

    def append_log(self, text: str):
        self.log_lines.append(text)

    def save(self, path: str, current_id: str = None, scenario_path: str = None):
        results = {}
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            status = self.model.get_status(index)
            if status != TaskStatus.NOT_TESTED:
                results[self.model.get_id(index)] = status.name

        data = {
            "scenario_path": scenario_path or self.model.scenario_name,
            "current_id": current_id,
            "results": results,
            "log": self.log_lines,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> tuple[str | None, str | None]:
        """Возвращает (current_id, scenario_path) для восстановления раннера/меты."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self.log_lines = data.get("log", [])

        for step_id, status_name in data.get("results", {}).items():
            self.model.set_status_by_id(step_id, TaskStatus[status_name])

        return data.get("current_id"), data.get("scenario_path")
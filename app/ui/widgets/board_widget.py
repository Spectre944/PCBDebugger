from __future__ import annotations

"""PCB annotation board with an Excalidraw-like UI.

Features:
- top toolbar: Select / Line / Rectangle / Text
- contextual property panel on the left
- three-dots menu for grid, snap, save/load and clear
- custom color palette + QColorDialog
- opacity and line width editing
- editable polyline handles
- editable rectangle and text (double click)
- multi-selection with Ctrl, grouping Ctrl+G / Ctrl+Shift+G
- group-wide name/color/width/opacity changes
- undo/redo, copy/paste, duplicate, delete
- JSON save/load
- PCB image drag & drop, zoom and pan
- visual effects (blink, highlight, pulse) for fault indication
- bulk transparency control
- rubber-band multi-selection
"""

import json
import math
from copy import deepcopy
from enum import Enum, auto
from typing import Optional, Union

from PySide6.QtCore import (
    Qt, QPoint, QPointF, QRectF, Signal, Slot, QTimer,
    QPropertyAnimation, QEasingCurve, Property, QObject,
)
from PySide6.QtGui import (
    QBrush, QColor, QCursor, QKeyEvent, QPainter, QPainterPath,
    QPen, QPixmap, QFont, QAction, QTransform,
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QFileDialog, QFrame, QGraphicsEllipseItem,
    QGraphicsItem, QGraphicsItemGroup, QGraphicsPathItem, QGraphicsPixmapItem,
    QGraphicsRectItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView,
    QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QSizePolicy,
    QSlider, QSpinBox, QToolButton, QVBoxLayout, QWidget, QInputDialog,
    QGraphicsDropShadowEffect, QCheckBox, QComboBox, QGroupBox,
    QRubberBand,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def color_with_alpha(value: str, opacity: int) -> QColor:
    c = QColor(value)
    c.setAlpha(max(0, min(255, int(opacity * 255 / 100))))
    return c


PALETTE = [
    "#ff5252", "#ff9800", "#ffd23f", "#4cd964", "#00c853",
    "#2b8aef", "#00bcd4", "#9c6cff", "#ff4fa3", "#ffffff",
]


class ToolMode:
    SELECT = "select"
    DRAW = "draw"
    RECT = "rect"
    TEXT = "text"
    EDIT = SELECT


# ---------------------------------------------------------------------------
# Effect types
# ---------------------------------------------------------------------------
class EffectType(Enum):
    NONE = auto()
    BLINK = auto()          # мигание (вкл/выкл)
    HIGHLIGHT = auto()      # яркая подсветка (glow)
    PULSE = auto()          # плавная пульсация прозрачности
    COLOR_CYCLE = auto()    # переключение цветов (красный/жёлтый)
    THICK_BLINK = auto()    # мигание с увеличенной толщиной


EFFECT_NAMES = {
    "none": EffectType.NONE,
    "blink": EffectType.BLINK,
    "highlight": EffectType.HIGHLIGHT,
    "pulse": EffectType.PULSE,
    "color_cycle": EffectType.COLOR_CYCLE,
    "thick_blink": EffectType.THICK_BLINK,
}

EFFECT_LABELS = {
    EffectType.NONE: "Нет эффекта",
    EffectType.BLINK: "Мигание",
    EffectType.HIGHLIGHT: "Подсветка (glow)",
    EffectType.PULSE: "Пульсация",
    EffectType.COLOR_CYCLE: "Цвет. цикл",
    EffectType.THICK_BLINK: "Толстое мигание",
}


# ---------------------------------------------------------------------------
# Effect controller — manages timers and animation state for one item
# ---------------------------------------------------------------------------
class EffectController(QObject):
    """Attaches a visual effect to an AnnotationItemMixin-compatible item."""

    def __init__(self, target, effect_type: EffectType = EffectType.NONE,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._target = target
        self._effect_type = EffectType.NONE
        self._timer = QTimer(self)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self._tick)
        self._phase = 0  # generic phase counter
        self._original_color: str | None = None
        self._original_width: float | None = None
        self._original_opacity: int | None = None
        self._glow_effect: QGraphicsDropShadowEffect | None = None

        if effect_type != EffectType.NONE:
            self.start(effect_type)

    # ---- public API --------------------------------------------------------
    @property
    def effect_type(self) -> EffectType:
        return self._effect_type

    def start(self, effect_type: EffectType):
        self.stop()  # clear previous
        self._effect_type = effect_type
        if effect_type == EffectType.NONE:
            return
        self._save_originals()
        if effect_type == EffectType.HIGHLIGHT:
            self._apply_highlight()
            return  # no timer needed, static effect
        interval_map = {
            EffectType.BLINK: 500,
            EffectType.PULSE: 60,
            EffectType.COLOR_CYCLE: 700,
            EffectType.THICK_BLINK: 500,
        }
        self._timer.setInterval(interval_map.get(effect_type, 400))
        self._phase = 0
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self._remove_glow()
        self._restore_originals()
        self._effect_type = EffectType.NONE
        self._phase = 0

    # ---- internals ---------------------------------------------------------
    def _save_originals(self):
        t = self._target
        self._original_color = t.color
        self._original_width = t.width
        self._original_opacity = t.opacity

    def _restore_originals(self):
        t = self._target
        if self._original_color is not None:
            t.color = self._original_color
        if self._original_width is not None:
            t.width = self._original_width
        if self._original_opacity is not None:
            t.opacity = self._original_opacity
        t.apply_style()
        self._original_color = None
        self._original_width = None
        self._original_opacity = None

    def _apply_highlight(self):
        t = self._target
        if not isinstance(t, QGraphicsItem):
            return
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(32)
        glow.setOffset(0, 0)
        glow.setColor(QColor(self._original_color or "#ff5252"))
        t.setGraphicsEffect(glow)
        self._glow_effect = glow
        # Also brighten the item itself
        bright = QColor(self._original_color or "#ff5252").lighter(150)
        t.color = bright.name()
        t.opacity = 100
        t.apply_style()

    def _remove_glow(self):
        if self._glow_effect is not None:
            t = self._target
            if isinstance(t, QGraphicsItem):
                t.setGraphicsEffect(None)
            self._glow_effect = None

    @Slot()
    def _tick(self):
        t = self._target
        et = self._effect_type
        self._phase += 1

        if et == EffectType.BLINK:
            visible = (self._phase % 2 == 0)
            if isinstance(t, QGraphicsItem):
                t.opacity = self._original_opacity if visible else 0
                t.apply_style()

        elif et == EffectType.PULSE:
            # smooth sine-wave opacity
            val = (math.sin(self._phase * 0.15) + 1.0) / 2.0  # 0..1
            op = int(20 + val * (self._original_opacity - 20))
            t.opacity = max(0, min(100, op))
            t.apply_style()

        elif et == EffectType.COLOR_CYCLE:
            colors = ["#ff0000", "#ffff00", "#ff5500", "#ff0066"]
            t.color = colors[self._phase % len(colors)]
            t.apply_style()

        elif et == EffectType.THICK_BLINK:
            if self._phase % 2 == 0:
                t.width = self._original_width
                t.opacity = self._original_opacity
            else:
                t.width = self._original_width * 3
                t.opacity = self._original_opacity
            t.apply_style()


# ---------------------------------------------------------------------------
# Line handles
# ---------------------------------------------------------------------------
class LineHandle(QGraphicsEllipseItem):
    RADIUS = 5

    def __init__(self, owner: "EditableLine", index: int, pos: QPointF):
        super().__init__(-self.RADIUS, -self.RADIUS,
                         self.RADIUS * 2, self.RADIUS * 2)
        self.owner = owner
        self.index = index
        self.setPos(pos)
        self.setZValue(1000)
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#2b8aef"), 1.5))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setVisible(False)
        self.setAcceptHoverEvents(True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            view = self.owner.view
            if view and view.snap_to_grid:
                return view.snap_point(value)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.owner.update_point(self.index, self.pos())
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        self.owner.remove_point(self.index)
        event.accept()

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#2b8aef")))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(QColor("#ffffff")))
        super().hoverLeaveEvent(event)


# ---------------------------------------------------------------------------
# Base annotation item
# ---------------------------------------------------------------------------
class AnnotationItemMixin:
    name: str
    color: str
    opacity: int
    width: float
    _effect_ctrl: EffectController | None

    def set_style(self, color=None, width=None, opacity=None):
        if color is not None:
            self.color = color
        if width is not None:
            self.width = float(width)
        if opacity is not None:
            self.opacity = int(opacity)
        self.apply_style()

    def apply_style(self):
        raise NotImplementedError

    # ---- effect API --------------------------------------------------------
    def apply_effect(self, effect_type: EffectType | str):
        """Apply a visual effect by type enum or string name."""
        if isinstance(effect_type, str):
            effect_type = EFFECT_NAMES.get(effect_type.lower(), EffectType.NONE)
        ctrl = getattr(self, "_effect_ctrl", None)
        if ctrl is None:
            ctrl = EffectController(self)
            self._effect_ctrl = ctrl
        ctrl.start(effect_type)

    def remove_effect(self):
        """Remove any active effect."""
        ctrl = getattr(self, "_effect_ctrl", None)
        if ctrl is not None:
            ctrl.stop()

    def current_effect(self) -> EffectType:
        ctrl = getattr(self, "_effect_ctrl", None)
        return ctrl.effect_type if ctrl else EffectType.NONE


class EditableLine(QGraphicsPathItem, AnnotationItemMixin):
    def __init__(self, color="#ff5252", width=3.0, name="", opacity=100):
        super().__init__()
        self.points: list[QPointF] = []
        self.handles: list[LineHandle] = []
        self.color = color
        self.width = float(width)
        self.name = name
        self.opacity = int(opacity)
        self.view: Optional["BoardView"] = None
        self._effect_ctrl: EffectController | None = None
        self.setZValue(10)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.apply_style()

    def apply_style(self):
        pen = QPen(color_with_alpha(self.color, self.opacity), self.width)
        pen.setCosmetic(True)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

    def shape(self) -> QPainterPath:
        """Wider shape for easier mouse picking."""
        stroker = QPainterPath()
        if not self.points:
            return stroker
        from PySide6.QtGui import QPainterPathStroker
        s = QPainterPathStroker()
        s.setWidth(max(self.width, 10))
        return s.createStroke(self.path())

    def add_point(self, pos):
        self.points.append(QPointF(pos))
        h = LineHandle(self, len(self.points) - 1, pos)
        self.handles.append(h)
        if self.scene():
            self.scene().addItem(h)
        h.setVisible(self.isSelected())
        self._rebuild()

    def update_point(self, index, pos):
        if 0 <= index < len(self.points):
            self.points[index] = QPointF(pos)
            self._rebuild()

    def remove_point(self, index):
        if len(self.points) <= 2:
            return
        self.points.pop(index)
        h = self.handles.pop(index)
        if h.scene():
            h.scene().removeItem(h)
        for i, handle in enumerate(self.handles):
            handle.index = i
        self._rebuild()

    def insert_point_near(self, pos):
        if len(self.points) < 2:
            self.add_point(pos)
            return
        best_i, best_d = 0, None
        for i in range(len(self.points) - 1):
            d = self._point_to_segment_dist(pos, self.points[i], self.points[i + 1])
            if best_d is None or d < best_d:
                best_i, best_d = i, d
        at = best_i + 1
        self.points.insert(at, QPointF(pos))
        h = LineHandle(self, at, pos)
        self.handles.insert(at, h)
        if self.scene():
            self.scene().addItem(h)
        for i, handle in enumerate(self.handles):
            handle.index = i
        h.setVisible(self.isSelected())
        self._rebuild()

    @staticmethod
    def _point_to_segment_dist(p, a, b):
        ax, ay, bx, by, px, py = a.x(), a.y(), b.x(), b.y(), p.x(), p.y()
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) /
                         (dx * dx + dy * dy)))
        cx, cy = ax + t * dx, ay + t * dy
        return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

    def _rebuild(self):
        path = QPainterPath()
        if self.points:
            path.moveTo(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)
        self.setPath(path)

    def set_editable(self, editable):
        for h in self.handles:
            h.setVisible(editable and self.parentItem() is None)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.set_editable(bool(value))
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        if self.view and self.parentItem() is None:
            pos = event.pos()
            if self.view.snap_to_grid:
                pos = self.view.snap_point(pos)
            self.insert_point_near(pos)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def remove_from_scene(self):
        self.remove_effect()
        for h in list(self.handles):
            if h.scene():
                h.scene().removeItem(h)
        self.handles.clear()
        if self.scene():
            self.scene().removeItem(self)

    def to_dict(self):
        return {
            "type": "line", "name": self.name,
            "points": [[p.x(), p.y()] for p in self.points],
            "color": self.color, "width": self.width, "opacity": self.opacity,
        }


class EditableRect(QGraphicsRectItem, AnnotationItemMixin):
    def __init__(self, rect=QRectF(), color="#ff5252", width=3,
                 name="", opacity=100):
        super().__init__(rect)
        self.name = name
        self.color = color
        self.width = float(width)
        self.opacity = int(opacity)
        self.view: Optional["BoardView"] = None
        self._effect_ctrl: EffectController | None = None
        self.setZValue(10)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.apply_style()

    def apply_style(self):
        self.setPen(QPen(color_with_alpha(self.color, self.opacity), self.width))
        self.setBrush(Qt.BrushStyle.NoBrush)

    def to_dict(self):
        r = self.rect()
        return {"type": "rect", "name": self.name,
                "rect": [r.x(), r.y(), r.width(), r.height()],
                "color": self.color, "width": self.width,
                "opacity": self.opacity}

    def mouseDoubleClickEvent(self, event):
        if self.view:
            self.view.edit_item_name(self)
        event.accept()


class EditableText(QGraphicsTextItem, AnnotationItemMixin):
    def __init__(self, text="Text", pos=QPointF(), color="#ffffff",
                 name="", opacity=100):
        super().__init__(text)
        self.name = name
        self.color = color
        self.opacity = int(opacity)
        self.width = 1.0
        self.font_size = 18
        self.view: Optional["BoardView"] = None
        self._effect_ctrl: EffectController | None = None
        self.setPos(pos)
        self.setZValue(20)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setFont(QFont("Segoe UI", self.font_size))
        self.apply_style()

    def apply_style(self):
        c = color_with_alpha(self.color, self.opacity)
        self.setDefaultTextColor(c)

    def mouseDoubleClickEvent(self, event):
        if self.view:
            self.view.edit_text(self)
        event.accept()

    def to_dict(self):
        return {"type": "text", "name": self.name,
                "text": self.toPlainText(),
                "pos": [self.pos().x(), self.pos().y()],
                "color": self.color,
                "opacity": self.opacity, "font_size": self.font_size}


class GroupItem(QGraphicsItemGroup, AnnotationItemMixin):
    def __init__(self, name="Group", color="#ffffff", width=3, opacity=100):
        super().__init__()
        self.name = name
        self.color = color
        self.width = float(width)
        self.opacity = int(opacity)
        self._effect_ctrl: EffectController | None = None
        self.setZValue(30)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setHandlesChildEvents(False)   # allow child picking
        self.apply_style()

    def apply_style(self):
        for child in self.childItems():
            if isinstance(child, AnnotationItemMixin):
                child.set_style(color=self.color, width=self.width,
                                opacity=self.opacity)

    def apply_effect(self, effect_type: EffectType | str):
        """Apply effect to entire group — propagate to children."""
        for child in self.childItems():
            if isinstance(child, AnnotationItemMixin):
                child.apply_effect(effect_type)

    def remove_effect(self):
        for child in self.childItems():
            if isinstance(child, AnnotationItemMixin):
                child.remove_effect()

    def add_child(self, item):
        item.setSelected(False)
        item.setParentItem(self)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        if isinstance(item, EditableLine):
            item.set_editable(False)
        self.apply_style()

    def ungroup_children(self):
        children = list(self.childItems())
        for child in children:
            child.setParentItem(None)
            child.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            if isinstance(child, EditableLine):
                child.view = getattr(self, "view", None)
        return children


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
class BoardScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._bg: Optional[QGraphicsPixmapItem] = None
        self.show_grid = True
        self.grid_size = 20

    def set_background(self, pixmap):
        if self._bg:
            self.removeItem(self._bg)
        self._bg = self.addPixmap(pixmap)
        self._bg.setZValue(-100)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.update()

    def set_grid_visible(self, visible):
        self.show_grid = bool(visible)
        self.update()

    def set_grid_size(self, size):
        self.grid_size = max(1, int(size))
        self.update()

    def drawForeground(self, painter, rect):
        if not self.show_grid or not self._bg or self.grid_size <= 0:
            return
        bounds = self.sceneRect().intersected(rect)
        if bounds.isEmpty():
            return
        step = self.grid_size
        left = int(bounds.left()) - int(bounds.left()) % step
        top = int(bounds.top()) - int(bounds.top()) % step
        painter.save()
        painter.setClipRect(bounds)
        pen = QPen(QColor(255, 255, 255, 38))
        pen.setWidth(0)
        painter.setPen(pen)
        x = left
        while x <= bounds.right():
            painter.drawLine(QPointF(x, bounds.top()),
                             QPointF(x, bounds.bottom()))
            x += step
        y = top
        while y <= bounds.bottom():
            painter.drawLine(QPointF(bounds.left(), y),
                             QPointF(bounds.right(), y))
            y += step
        painter.restore()


# ---------------------------------------------------------------------------
# View / editor
# ---------------------------------------------------------------------------
class BoardView(QGraphicsView):
    toolChanged = Signal(str)
    selectionInfoChanged = Signal()
    historyChanged = Signal(bool, bool)

    # Signal emitted when an effect is applied: (item_name, effect_name)
    effectApplied = Signal(str, str)
    # Signal emitted when an effect is removed: (item_name,)
    effectRemoved = Signal(str)

    def __init__(self, scene: BoardScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#111218")))
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._panning = False
        self._pan_start = QPoint()
        self._space = False
        self.tool = ToolMode.SELECT
        self.current_line: Optional[EditableLine] = None
        self.lines: list[EditableLine] = []
        self.snap_to_grid = True
        self.draw_color = PALETTE[0]
        self.draw_width = 3.0
        self.draw_opacity = 100
        self._history: list[dict] = []
        self._history_index = -1
        self._clipboard: Optional[list[dict]] = None
        self._custom_color = PALETTE[0]

        # Rubber-band selection support
        self._rubber_band: QRubberBand | None = None
        self._rubber_origin = QPoint()
        self._rubber_active = False

        # Bulk transparency state
        self._all_dimmed = False
        self._dim_opacity = 15  # opacity when dimmed

        self.scene().selectionChanged.connect(self.selectionInfoChanged)
        self._push_history()

    # ---- selection ---------------------------------------------------------
    def top_level_annotation(self, item):
        while item is not None and item.parentItem() is not None:
            if isinstance(item.parentItem(), GroupItem):
                item = item.parentItem()
            else:
                break
        return item

    def selected_items(self):
        result = []
        seen = set()
        for item in self.scene().selectedItems():
            top = self.top_level_annotation(item)
            if isinstance(top, (EditableLine, EditableRect,
                                EditableText, GroupItem)):
                if id(top) not in seen:
                    seen.add(id(top))
                    result.append(top)
        return result

    def selected_item(self):
        items = self.selected_items()
        return items[0] if len(items) == 1 else None

    def _selected_line(self):
        item = self.selected_item()
        return item if isinstance(item, EditableLine) else None

    # ---- tools -------------------------------------------------------------
    def set_tool(self, tool):
        if self.tool == ToolMode.DRAW and tool != ToolMode.DRAW:
            self._finish_current_line()
        self.tool = tool
        # Enable/disable selection flag for annotation items
        for item in self.scene().items():
            if isinstance(item, (EditableLine, EditableRect,
                                 EditableText, GroupItem)):
                if item.parentItem() is None:
                    item.setFlag(
                        QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                        tool == ToolMode.SELECT)
        cursor = (QCursor(Qt.CursorShape.CrossCursor)
                  if tool != ToolMode.SELECT
                  else QCursor(Qt.CursorShape.ArrowCursor))
        self.viewport().setCursor(cursor)
        self.toolChanged.emit(tool)

    def snap_point(self, pos):
        size = self.scene().grid_size
        if size > 0:
            return QPointF(round(pos.x() / size) * size,
                           round(pos.y() / size) * size)
        return pos

    # ---- style -------------------------------------------------------------
    def _apply_selected_style(self, **kwargs):
        items = self.selected_items()
        if not items:
            return
        self._push_history()
        for item in items:
            if isinstance(item, (GroupItem, AnnotationItemMixin)):
                item.set_style(**kwargs)
        self.selectionInfoChanged.emit()

    def set_draw_color(self, color):
        self.draw_color = color
        self._apply_selected_style(color=color)

    def set_draw_width(self, width):
        self.draw_width = float(width)
        self._apply_selected_style(width=width)

    def set_draw_opacity(self, opacity):
        self.draw_opacity = int(opacity)
        self._apply_selected_style(opacity=opacity)

    # ---- effects API (slots) -----------------------------------------------
    @Slot(str, str)
    def apply_effect_by_name(self, item_name: str, effect_name: str):
        """Apply an effect to all items with the given name.

        Call from external code (e.g. from a processor fault handler):
            board.apply_effect_by_name("VCC_3V3", "blink")
        """
        effect = EFFECT_NAMES.get(effect_name.lower(), EffectType.NONE)
        found = False
        for item in self.annotation_items():
            if self._match_name(item, item_name):
                item.apply_effect(effect)
                found = True
        if found:
            self.effectApplied.emit(item_name, effect_name)

    @Slot(str)
    def remove_effect_by_name(self, item_name: str):
        """Remove effects from all items with the given name."""
        for item in self.annotation_items():
            if self._match_name(item, item_name):
                item.remove_effect()
        self.effectRemoved.emit(item_name)

    @Slot()
    def remove_all_effects(self):
        """Clear effects from every annotation item."""
        for item in self.annotation_items():
            item.remove_effect()
            if isinstance(item, GroupItem):
                for child in item.childItems():
                    if isinstance(child, AnnotationItemMixin):
                        child.remove_effect()

    @Slot(str, str)
    def apply_effect_to_selected(self, effect_name: str,
                                 _unused: str = ""):
        """Apply effect to currently selected items."""
        effect = EFFECT_NAMES.get(effect_name.lower(), EffectType.NONE)
        for item in self.selected_items():
            item.apply_effect(effect)

    @Slot()
    def remove_effect_from_selected(self):
        for item in self.selected_items():
            item.remove_effect()

    @staticmethod
    def _match_name(item, name: str) -> bool:
        return getattr(item, "name", "") == name

    # ---- bulk transparency -------------------------------------------------
    @Slot(bool)
    def set_all_dimmed(self, dimmed: bool):
        """Make all annotation items semi-transparent (dim) so that
        highlighted fault lines stand out."""
        self._all_dimmed = dimmed
        op = self._dim_opacity if dimmed else 100
        for item in self.annotation_items():
            # Don't dim items that have an active effect
            if dimmed and item.current_effect() != EffectType.NONE:
                continue
            if isinstance(item, GroupItem):
                has_effect = False
                for child in item.childItems():
                    if isinstance(child, AnnotationItemMixin):
                        if child.current_effect() != EffectType.NONE:
                            has_effect = True
                            break
                if has_effect:
                    continue
            item.set_style(opacity=op)

    @Slot()
    def toggle_dim(self):
        self.set_all_dimmed(not self._all_dimmed)

    @Slot(int)
    def set_dim_opacity(self, opacity: int):
        self._dim_opacity = max(0, min(100, opacity))
        if self._all_dimmed:
            self.set_all_dimmed(True)

    # ---- drawing -----------------------------------------------------------
    def _start_or_continue_line(self, scene_pos):
        if self.snap_to_grid:
            scene_pos = self.snap_point(scene_pos)
        if self.current_line is None:
            self._push_history()
            self.current_line = EditableLine(
                self.draw_color, self.draw_width, "", self.draw_opacity)
            self.current_line.view = self
            self.scene().addItem(self.current_line)
            self.lines.append(self.current_line)
            self.scene().clearSelection()
            self.current_line.setSelected(True)
        self.current_line.add_point(scene_pos)

    def _finish_current_line(self):
        if not self.current_line:
            return
        if len(self.current_line.points) < 2:
            self.current_line.remove_from_scene()
            if self.current_line in self.lines:
                self.lines.remove(self.current_line)
        self.current_line = None
        self.selectionInfoChanged.emit()

    def cancel_current_line(self):
        if self.current_line:
            self.current_line.remove_from_scene()
            if self.current_line in self.lines:
                self.lines.remove(self.current_line)
            self.current_line = None

    def create_rectangle(self, start, end):
        self._push_history()
        if self.snap_to_grid:
            start, end = self.snap_point(start), self.snap_point(end)
        rect = QRectF(start, end).normalized()
        if rect.width() < 2 or rect.height() < 2:
            return
        item = EditableRect(rect, self.draw_color, self.draw_width,
                            "", self.draw_opacity)
        item.view = self
        self.scene().addItem(item)
        self.scene().clearSelection()
        item.setSelected(True)

    def create_text(self, pos):
        text, ok = QInputDialog.getText(self, "Новый текст", "Текст:")
        if not ok or not text:
            return
        self._push_history()
        if self.snap_to_grid:
            pos = self.snap_point(pos)
        item = EditableText(text, pos, self.draw_color, "", self.draw_opacity)
        item.view = self
        self.scene().addItem(item)
        self.scene().clearSelection()
        item.setSelected(True)

    def edit_text(self, item):
        text, ok = QInputDialog.getText(
            self, "Редактирование текста", "Текст:",
            text=item.toPlainText())
        if ok and text != item.toPlainText():
            self._push_history()
            item.setPlainText(text)

    def edit_item_name(self, item):
        text, ok = QInputDialog.getText(
            self, "Имя объекта", "Имя:", text=item.name)
        if ok:
            self._push_history()
            item.name = text.strip()
            self.selectionInfoChanged.emit()

    # ---- grouping ----------------------------------------------------------
    def group_selected(self):
        items = self.selected_items()
        if len(items) < 2:
            return
        self._push_history()
        group = GroupItem("Group", self.draw_color,
                          self.draw_width, self.draw_opacity)
        group.view = self
        self.scene().addItem(group)
        for item in items:
            if item is group:
                continue
            item.setSelected(False)
            group.add_child(item)
        self.scene().clearSelection()
        group.setSelected(True)
        self.selectionInfoChanged.emit()

    def ungroup_selected(self):
        groups = [x for x in self.selected_items()
                  if isinstance(x, GroupItem)]
        if not groups:
            return
        self._push_history()
        children = []
        for group in groups:
            children.extend(group.ungroup_children())
            if group.scene():
                self.scene().removeItem(group)
        self.scene().clearSelection()
        for item in children:
            item.setSelected(True)
        self.selectionInfoChanged.emit()

    @Slot(list)
    def group_items_by_names(self, names: list[str],
                             group_name: str = "Group"):
        """Find items by name list and group them together."""
        items_to_group = []
        for item in self.annotation_items():
            if getattr(item, "name", "") in names:
                items_to_group.append(item)
        if len(items_to_group) < 2:
            return
        self.scene().clearSelection()
        for item in items_to_group:
            item.setSelected(True)
        self.group_selected()
        # Rename the new group
        grp = self.selected_item()
        if isinstance(grp, GroupItem):
            grp.name = group_name
        self.selectionInfoChanged.emit()

    # ---- deletion ----------------------------------------------------------
    def delete_selected(self):
        items = self.selected_items()
        if not items:
            return
        self._push_history()
        for item in items:
            if isinstance(item, GroupItem):
                item.remove_effect()
                for child in list(item.childItems()):
                    if isinstance(child, AnnotationItemMixin):
                        child.remove_effect()
                    if isinstance(child, EditableLine):
                        for h in child.handles:
                            if h.scene():
                                self.scene().removeItem(h)
                self.scene().removeItem(item)
            elif isinstance(item, EditableLine):
                item.remove_from_scene()
            else:
                item.remove_effect()
                self.scene().removeItem(item)
        self.selectionInfoChanged.emit()

    def clear_all(self):
        if not self.selected_items() and not self.annotation_items():
            return
        self._push_history()
        self._clear_annotations()
        self.selectionInfoChanged.emit()

    def annotation_items(self):
        return [i for i in self.scene().items()
                if isinstance(i, (EditableLine, EditableRect,
                                  EditableText, GroupItem))
                and i.parentItem() is None]

    def _clear_annotations(self):
        for item in list(self.annotation_items()):
            if isinstance(item, GroupItem):
                item.remove_effect()
                for child in list(item.childItems()):
                    if isinstance(child, AnnotationItemMixin):
                        child.remove_effect()
                    if isinstance(child, EditableLine):
                        for h in child.handles:
                            if h.scene():
                                self.scene().removeItem(h)
                self.scene().removeItem(item)
            elif isinstance(item, EditableLine):
                item.remove_from_scene()
            else:
                item.remove_effect()
                self.scene().removeItem(item)
        self.lines.clear()
        self.current_line = None

    # ---- undo/redo ---------------------------------------------------------
    def _snapshot(self):
        return self.annotations_to_dict()

    def _push_history(self):
        snap = self._snapshot()
        if (self._history_index >= 0
                and self._history[self._history_index] == snap):
            return
        self._history = self._history[:self._history_index + 1]
        self._history.append(deepcopy(snap))
        self._history_index = len(self._history) - 1
        self.historyChanged.emit(self._history_index > 0, False)

    def _restore_history(self, snap):
        self._clear_annotations()
        self._load_annotations_dict(snap, select=False)
        self.selectionInfoChanged.emit()

    def undo(self):
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._restore_history(self._history[self._history_index])
        self.historyChanged.emit(
            self._history_index > 0,
            self._history_index < len(self._history) - 1)

    def redo(self):
        if self._history_index >= len(self._history) - 1:
            return
        self._history_index += 1
        self._restore_history(self._history[self._history_index])
        self.historyChanged.emit(
            self._history_index > 0,
            self._history_index < len(self._history) - 1)

    # ---- copy/paste --------------------------------------------------------
    def copy_selected(self):
        items = self.selected_items()
        if items:
            self._clipboard = [self._item_to_dict(i) for i in items]

    def paste(self):
        if not self._clipboard:
            return
        self._push_history()
        self.scene().clearSelection()
        for data in self._clipboard:
            item = self._item_from_dict(data, QPointF(20, 20))
            if item:
                self._add_item_to_scene(item, select=True)

    def duplicate_selected(self):
        self.copy_selected()
        self.paste()

    # ---- serialization -----------------------------------------------------
    def _item_to_dict(self, item):
        if isinstance(item, GroupItem):
            return {
                "type": "group", "name": item.name, "color": item.color,
                "width": item.width, "opacity": item.opacity,
                "children": [self._item_to_dict(c)
                             for c in item.childItems()
                             if isinstance(c, AnnotationItemMixin)]}
        return item.to_dict()

    def _item_from_dict(self, data, offset=QPointF()):
        typ = data.get("type")
        if typ == "line":
            item = EditableLine(
                data.get("color", "#ff5252"), data.get("width", 3),
                data.get("name", ""), data.get("opacity", 100))
            item.view = self
            for x, y in data.get("points", []):
                item.add_point(QPointF(x + offset.x(), y + offset.y()))
            return item
        if typ == "rect":
            x, y, w, h = data.get("rect", [0, 0, 100, 60])
            item = EditableRect(
                QRectF(x + offset.x(), y + offset.y(), w, h),
                data.get("color", "#ff5252"), data.get("width", 3),
                data.get("name", ""), data.get("opacity", 100))
            item.view = self
            return item
        if typ == "text":
            x, y = data.get("pos", [0, 0])
            item = EditableText(
                data.get("text", "Text"),
                QPointF(x + offset.x(), y + offset.y()),
                data.get("color", "#ffffff"),
                data.get("name", ""), data.get("opacity", 100))
            item.font_size = data.get("font_size", 18)
            item.setFont(QFont("Segoe UI", item.font_size))
            item.view = self
            return item
        if typ == "group":
            group = GroupItem(
                data.get("name", "Group"), data.get("color", "#ffffff"),
                data.get("width", 3), data.get("opacity", 100))
            group.view = self
            for child_data in data.get("children", []):
                child = self._item_from_dict(child_data, offset)
                if child:
                    group.add_child(child)
            group.apply_style()
            return group
        return None

    def annotations_to_dict(self):
        return {"version": 2,
                "items": [self._item_to_dict(i)
                          for i in self.annotation_items()]}

    def _add_item_to_scene(self, item, select=False):
        self.scene().addItem(item)
        if isinstance(item, EditableLine):
            for handle in item.handles:
                if handle.scene() is None:
                    self.scene().addItem(handle)
                handle.setVisible(False)
        elif isinstance(item, GroupItem):
            for child in item.childItems():
                if isinstance(child, EditableLine):
                    for handle in child.handles:
                        if handle.scene() is None:
                            self.scene().addItem(handle)
                        handle.setVisible(False)
        if select:
            item.setSelected(True)
        self._register_item(item)

    def _load_annotations_dict(self, data, select=False):
        for item_data in data.get("items", []):
            item = self._item_from_dict(item_data)
            if item:
                self._add_item_to_scene(item, select)

        # Compatibility with old files.
        for line_data in data.get("lines", []):
            item = self._item_from_dict({"type": "line", **line_data})
            if item:
                self._add_item_to_scene(item)
                self.lines.append(item)

    def _register_item(self, item):
        if isinstance(item, EditableLine) and item not in self.lines:
            self.lines.append(item)
        if isinstance(item, GroupItem):
            for child in item.childItems():
                self._register_item(child)

    def load_annotations_dict(self, data):
        self._clear_annotations()
        self._load_annotations_dict(data)
        self._push_history()
        self.selectionInfoChanged.emit()

    def get_line(self, name) -> Optional[EditableLine]:
        for line in self.lines:
            if line.name == name:
                return line
        return None

    def get_lines_by_name(self, name):
        return [line for line in self.lines if line.name == name]

    def get_item_by_name(self, name) -> Optional[AnnotationItemMixin]:
        for item in self.annotation_items():
            if getattr(item, "name", "") == name:
                return item
        return None

    def get_items_by_name(self, name) -> list:
        return [item for item in self.annotation_items()
                if getattr(item, "name", "") == name]

    def set_snap_to_grid(self, enabled):
        self.snap_to_grid = bool(enabled)

    # ---- events ------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._pan_start = event.pos()
            self.viewport().setCursor(
                QCursor(Qt.CursorShape.ClosedHandCursor))
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self.tool == ToolMode.DRAW:
                self._start_or_continue_line(
                    self.mapToScene(event.pos()))
                return
            if self.tool == ToolMode.RECT:
                self._rect_start = self.mapToScene(event.pos())
                self._rect_dragging = True
                return
            if self.tool == ToolMode.TEXT:
                self.create_text(self.mapToScene(event.pos()))
                return

            # SELECT mode: check if clicking on empty space -> rubber band
            if self.tool == ToolMode.SELECT:
                item_at = self.itemAt(event.pos())
                # If clicking on annotation item (or its handle), let
                # default handling work
                top = self.top_level_annotation(item_at) if item_at else None
                is_annotation = isinstance(
                    top, (EditableLine, EditableRect,
                          EditableText, GroupItem))
                is_handle = isinstance(item_at, LineHandle)

                if not is_annotation and not is_handle:
                    # Start rubber-band if no Ctrl held (clear selection)
                    if not (event.modifiers()
                            & Qt.KeyboardModifier.ControlModifier):
                        self.scene().clearSelection()
                    self._rubber_origin = event.pos()
                    if self._rubber_band is None:
                        self._rubber_band = QRubberBand(
                            QRubberBand.Shape.Rectangle, self.viewport())
                    self._rubber_band.setGeometry(
                        QRectF(self._rubber_origin,
                               self._rubber_origin).toRect())
                    self._rubber_band.show()
                    self._rubber_active = True
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            d = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - d.y())
            return

        if self._rubber_active and self._rubber_band is not None:
            rect = QRectF(self._rubber_origin, event.pos()).normalized()
            self._rubber_band.setGeometry(rect.toRect())
            return

        if getattr(self, "_rect_dragging", False):
            self.viewport().update()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self._panning:
            self._panning = False
            self.viewport().setCursor(
                QCursor(Qt.CursorShape.ArrowCursor))
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if getattr(self, "_rect_dragging", False):
                self._rect_dragging = False
                self.create_rectangle(
                    self._rect_start, self.mapToScene(event.pos()))
                self.set_tool(ToolMode.SELECT)
                return

            if self._rubber_active and self._rubber_band is not None:
                self._rubber_active = False
                self._rubber_band.hide()
                # Select items within the rubber-band area
                rect = QRectF(
                    self.mapToScene(self._rubber_origin),
                    self.mapToScene(event.pos())).normalized()
                for item in self.scene().items(rect):
                    top = self.top_level_annotation(item)
                    if isinstance(top, (EditableLine, EditableRect,
                                        EditableText, GroupItem)):
                        if top.parentItem() is None:
                            top.setSelected(True)
                self.selectionInfoChanged.emit()
                return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if (self.tool == ToolMode.DRAW
                and event.button() == Qt.MouseButton.LeftButton):
            self._finish_current_line()
            self.set_tool(ToolMode.SELECT)
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        key, mods = event.key(), event.modifiers()
        if key == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space = True
            self._panning = True
            self._pan_start = self.mapFromGlobal(QCursor.pos())
            return
        if mods & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Z:
                self.undo()
                return
            if key == Qt.Key.Key_Y:
                self.redo()
                return
            if key == Qt.Key.Key_C:
                self.copy_selected()
                return
            if key == Qt.Key.Key_V:
                self.paste()
                return
            if key == Qt.Key.Key_D:
                self.duplicate_selected()
                return
            if key == Qt.Key.Key_G:
                if mods & Qt.KeyboardModifier.ShiftModifier:
                    self.ungroup_selected()
                else:
                    self.group_selected()
                return
            if key == Qt.Key.Key_R and (
                    mods & Qt.KeyboardModifier.ShiftModifier):
                self.ungroup_selected()
                return
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            return
        if self.tool == ToolMode.DRAW:
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._finish_current_line()
                self.set_tool(ToolMode.SELECT)
                return
            if key == Qt.Key.Key_Escape:
                self.cancel_current_line()
                self.set_tool(ToolMode.SELECT)
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space = False
            self._panning = False
            self.viewport().setCursor(
                QCursor(Qt.CursorShape.ArrowCursor))
            return
        super().keyReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def fit(self):
        if not self.scene().sceneRect().isEmpty():
            self.fitInView(self.sceneRect(),
                           Qt.AspectRatioMode.KeepAspectRatio)


# ---------------------------------------------------------------------------
# Main widget
# ---------------------------------------------------------------------------
class BoardWidget(BoardView):
    _IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp",
                   ".webp", ".tif", ".tiff")

    def __init__(self, parent=None):
        self._scene = BoardScene()
        super().__init__(self._scene)
        self.setAcceptDrops(True)
        self._build_ui()
        self.scene().selectionChanged.connect(self._sync_property_panel)
        self._sync_property_panel()

    def _build_ui(self):
        self.toolbar = TopToolbar(self)
        self.toolbar.bind(self)
        self.properties = PropertiesPanel(self)
        self.properties.bind(self)
        self.menu_button = QToolButton(self)
        self.menu_button.setText("⋮")
        self.menu_button.setFixedSize(42, 42)
        self.menu_button.setStyleSheet(
            "QToolButton { background: rgba(25,26,33,225); color:#eee; "
            "border:1px solid rgba(255,255,255,35); border-radius:9px; "
            "font-size:22px; }")
        self.menu_button.clicked.connect(self._show_menu)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toolbar.adjustSize()
        self.toolbar.move(
            max(10, (self.width() - self.toolbar.width()) // 2), 10)
        self.properties.adjustSize()
        self.properties.move(10, 62)
        self.menu_button.move(
            self.width() - self.menu_button.width() - 12, 12)

    def _sync_property_panel(self):
        self.properties.set_item(self.selected_item())

    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background:#202127; color:#eee; "
            "border:1px solid #444; } "
            "QMenu::item:selected { background:#2b8aef; }")

        grid = menu.addAction(
            "✓ Сетка" if self.scene().show_grid else "Сетка")
        grid.triggered.connect(
            lambda: self.scene().set_grid_visible(
                not self.scene().show_grid))

        snap = menu.addAction(
            "✓ Прилипание" if self.snap_to_grid else "Прилипание")
        snap.triggered.connect(
            lambda: self.set_snap_to_grid(not self.snap_to_grid))

        grid_size = menu.addAction(
            f"Шаг сетки: {self.scene().grid_size}px")
        grid_size.triggered.connect(self._change_grid_size)

        menu.addSeparator()

        dim_label = ("✓ Все прозрачные" if self._all_dimmed
                     else "Все прозрачные")
        dim_action = menu.addAction(dim_label)
        dim_action.triggered.connect(self.toggle_dim)

        dim_val = menu.addAction(
            f"Прозрачность фона: {self._dim_opacity}%")
        dim_val.triggered.connect(self._change_dim_opacity)

        menu.addSeparator()

        # Effects submenu
        effects_menu = menu.addMenu("Эффекты")
        clear_fx = effects_menu.addAction("Снять все эффекты")
        clear_fx.triggered.connect(self.remove_all_effects)
        effects_menu.addSeparator()

        sel = self.selected_items()
        for etype, label in EFFECT_LABELS.items():
            if etype == EffectType.NONE:
                continue
            act = effects_menu.addAction(f"▸ {label}")
            act.setEnabled(len(sel) > 0)
            name = [k for k, v in EFFECT_NAMES.items()
                    if v == etype][0]
            act.triggered.connect(
                lambda _, n=name: self.apply_effect_to_selected(n))

        remove_sel_fx = effects_menu.addAction("Снять с выделенных")
        remove_sel_fx.setEnabled(len(sel) > 0)
        remove_sel_fx.triggered.connect(self.remove_effect_from_selected)

        menu.addSeparator()

        undo = menu.addAction("Отменить   Ctrl+Z")
        undo.setEnabled(self._history_index > 0)
        undo.triggered.connect(self.undo)
        redo = menu.addAction("Повторить   Ctrl+Y")
        redo.setEnabled(
            self._history_index < len(self._history) - 1)
        redo.triggered.connect(self.redo)

        menu.addSeparator()

        save = menu.addAction("Сохранить…")
        save.triggered.connect(self.save_annotations_dialog)
        load = menu.addAction("Загрузить…")
        load.triggered.connect(self.load_annotations_dialog)

        menu.addSeparator()

        clear = menu.addAction("Очистить всё")
        clear.triggered.connect(self.clear_all)

        menu.exec(self.menu_button.mapToGlobal(
            QPoint(0, self.menu_button.height())))

    def _change_grid_size(self):
        value, ok = QInputDialog.getInt(
            self, "Сетка", "Шаг сетки:",
            self.scene().grid_size, 1, 500)
        if ok:
            self.scene().set_grid_size(value)

    def _change_dim_opacity(self):
        value, ok = QInputDialog.getInt(
            self, "Прозрачность фона",
            "Прозрачность неактивных линий (0-100):",
            self._dim_opacity, 0, 100)
        if ok:
            self.set_dim_opacity(value)

    # drag & drop
    def _is_image_drop(self, event):
        if not event.mimeData().hasUrls():
            return False
        path = event.mimeData().urls()[0].toLocalFile().lower()
        return path.endswith(self._IMAGE_EXTS)

    def dragEnterEvent(self, event):
        if self._is_image_drop(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._is_image_drop(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if self._is_image_drop(event):
            if self.load_image(
                    event.mimeData().urls()[0].toLocalFile()):
                event.acceptProposedAction()
                return
        event.ignore()

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return False
        self.scene().set_background(pixmap)
        self.fit()
        return True

    def save_annotations_dialog(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить проект", "", "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.annotations_to_dict(), f,
                      ensure_ascii=False, indent=2)

    def load_annotations_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить проект", "", "JSON (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_annotations_dict(data)

    # Compatibility API
    def lines_to_dict(self):
        return self.annotations_to_dict()

    def load_lines_from_dict(self, data):
        self.load_annotations_dict(data)

    def rename_selected_line(self, name):
        item = self.selected_item()
        if item:
            self._push_history()
            item.name = name.strip()
            self.selectionInfoChanged.emit()


# ---------------------------------------------------------------------------
# Top toolbar
# ---------------------------------------------------------------------------
class TopToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbar")
        self.setStyleSheet("""
            QFrame#toolbar {
                background: rgba(28,29,36,235);
                border:1px solid rgba(255,255,255,35);
                border-radius:10px;
            }
            QPushButton {
                color:#ddd; background:transparent; border:0;
                border-radius:7px; padding:8px 12px;
            }
            QPushButton:hover { background:rgba(255,255,255,12); }
            QPushButton:checked { background:#2b8aef; color:white; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        self.buttons = {}
        for mode, label in [
            (ToolMode.SELECT, "↖  Выбор"),
            (ToolMode.DRAW, "╱  Линия"),
            (ToolMode.RECT, "□  Прямоугольник"),
            (ToolMode.TEXT, "T  Текст"),
        ]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.clicked.connect(
                lambda _, m=mode: self.board.set_tool(m))
            layout.addWidget(b)
            self.buttons[mode] = b
        self.buttons[ToolMode.SELECT].setChecked(True)

    def bind(self, board):
        self.board = board
        board.toolChanged.connect(self.sync)

    def sync(self, mode):
        for m, b in self.buttons.items():
            b.setChecked(m == mode)


# ---------------------------------------------------------------------------
# Property panel
# ---------------------------------------------------------------------------
class PropertiesPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = None
        self.item = None
        self._updating = False
        self.setObjectName("properties")
        self.setStyleSheet("""
            QFrame#properties {
                background:rgba(28,29,36,235);
                border:1px solid rgba(255,255,255,35);
                border-radius:10px;
            }
            QLabel { color:#aaa; font-size:11px; }
            QLineEdit, QSpinBox, QComboBox {
                background:rgba(255,255,255,12); color:#eee;
                border:1px solid rgba(255,255,255,35);
                border-radius:6px; padding:5px;
            }
            QComboBox::drop-down {
                border:0; width:20px;
            }
            QComboBox QAbstractItemView {
                background:#202127; color:#eee;
                selection-background-color:#2b8aef;
            }
            QSlider::groove:horizontal {
                height:4px; background:#555; border-radius:2px;
            }
            QSlider::handle:horizontal {
                width:12px; margin:-5px 0;
                background:#2b8aef; border-radius:6px;
            }
            QPushButton {
                color:#eee; background:rgba(255,255,255,12);
                border:1px solid rgba(255,255,255,35);
                border-radius:6px; padding:5px;
            }
            QPushButton:hover { background:rgba(255,255,255,22); }
            QCheckBox { color:#ccc; font-size:11px; }
        """)
        self.setFixedWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)

        title = QLabel("Свойства")
        title.setStyleSheet("font-size:14px;font-weight:600;color:#eee;")
        layout.addWidget(title)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Имя")
        layout.addWidget(QLabel("Имя"))
        layout.addWidget(self.name)
        self.name.editingFinished.connect(self._name_changed)

        layout.addWidget(QLabel("Цвет"))
        self.palette_layout = QHBoxLayout()
        self.palette_layout.setSpacing(4)
        layout.addLayout(self.palette_layout)
        for c in PALETTE:
            b = QPushButton()
            b.setFixedSize(20, 20)
            b.setStyleSheet(
                f"background:{c};"
                "border:1px solid rgba(255,255,255,80);"
                "border-radius:10px;")
            b.clicked.connect(lambda _, x=c: self._color(x))
            self.palette_layout.addWidget(b)
        custom = QPushButton("+")
        custom.setFixedSize(22, 22)
        custom.clicked.connect(self._custom)
        self.palette_layout.addWidget(custom)

        self.color_preview = QFrame()
        self.color_preview.setFixedHeight(6)
        layout.addWidget(self.color_preview)

        layout.addWidget(QLabel("Толщина"))
        self.width = QSlider(Qt.Orientation.Horizontal)
        self.width.setRange(1, 30)
        self.width.valueChanged.connect(self._width_changed)
        layout.addWidget(self.width)
        self.width_value = QLabel()
        layout.addWidget(self.width_value)

        layout.addWidget(QLabel("Прозрачность"))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(100)
        self.opacity.valueChanged.connect(self._opacity_changed)
        layout.addWidget(self.opacity)
        self.opacity_value = QLabel()
        layout.addWidget(self.opacity_value)

        # Effect selector
        layout.addWidget(QLabel("Эффект"))
        self.effect_combo = QComboBox()
        for etype, label in EFFECT_LABELS.items():
            name_key = [k for k, v in EFFECT_NAMES.items()
                        if v == etype][0]
            self.effect_combo.addItem(label, name_key)
        self.effect_combo.currentIndexChanged.connect(
            self._effect_changed)
        layout.addWidget(self.effect_combo)

        # Actions
        self.actions = QHBoxLayout()
        self.group_btn = QPushButton("Сгруппировать")
        self.ungroup_btn = QPushButton("Разгруппировать")
        self.actions.addWidget(self.group_btn)
        self.actions.addWidget(self.ungroup_btn)
        layout.addLayout(self.actions)
        self.group_btn.clicked.connect(
            lambda: self.board.group_selected())
        self.ungroup_btn.clicked.connect(
            lambda: self.board.ungroup_selected())

        # Dim all checkbox
        self.dim_check = QCheckBox("Приглушить все линии")
        self.dim_check.toggled.connect(self._dim_toggled)
        layout.addWidget(self.dim_check)

        self.hint = QLabel(
            "Ctrl+клик — несколько\n"
            "Ctrl+G — группа\n"
            "Ctrl+Shift+G — разгруппа\n"
            "Рамка — выделить область")
        self.hint.setStyleSheet("color:#777;font-size:10px;")
        layout.addWidget(self.hint)

        layout.addStretch()
        self.setVisible(False)

    def bind(self, board):
        self.board = board

    def set_item(self, item):
        self._updating = True
        self.item = item
        self.setVisible(item is not None)
        if item:
            self.name.setText(getattr(item, "name", ""))
            self.width.setValue(
                max(1, min(30, int(getattr(item, "width", 3)))))
            self.opacity.setValue(
                int(getattr(item, "opacity", 100)))
            self.width_value.setText(
                f"{getattr(item, 'width', 3):g}px")
            self.opacity_value.setText(
                f"{getattr(item, 'opacity', 100)}%")
            self.color_preview.setStyleSheet(
                f"background:{getattr(item, 'color', '#fff')};"
                "border-radius:3px;")
            # Sync effect combo
            current_effect = item.current_effect()
            for i in range(self.effect_combo.count()):
                key = self.effect_combo.itemData(i)
                if EFFECT_NAMES.get(key) == current_effect:
                    self.effect_combo.setCurrentIndex(i)
                    break

        self.ungroup_btn.setEnabled(isinstance(item, GroupItem))
        self.dim_check.setChecked(
            self.board._all_dimmed if self.board else False)
        self._updating = False

    def _name_changed(self):
        if self._updating or not self.item:
            return
        self.board._push_history()
        self.item.name = self.name.text().strip()
        self.board.selectionInfoChanged.emit()

    def _color(self, color):
        if not self.item:
            self.board.draw_color = color
            return
        self.board._apply_selected_style(color=color)
        self.set_item(self.board.selected_item())

    def _custom(self):
        current = QColor(
            getattr(self.item, "color", self.board.draw_color))
        color = QColorDialog.getColor(current, self, "Выбор цвета")
        if color.isValid():
            name = (color.name(QColor.NameFormat.HexArgb)
                    if color.alpha() < 255 else color.name())
            self._color(name)

    def _width_changed(self, value):
        if self._updating:
            return
        self.width_value.setText(f"{value}px")
        if self.item:
            self.board._apply_selected_style(width=float(value))

    def _opacity_changed(self, value):
        if self._updating:
            return
        self.opacity_value.setText(f"{value}%")
        if self.item:
            self.board._apply_selected_style(opacity=value)

    def _effect_changed(self, index):
        if self._updating or not self.item:
            return
        effect_name = self.effect_combo.itemData(index)
        if effect_name == "none":
            self.board.remove_effect_from_selected()
        else:
            self.board.apply_effect_to_selected(effect_name)

    def _dim_toggled(self, checked):
        if self._updating or not self.board:
            return
        self.board.set_all_dimmed(checked)


# Backwards-compatible name
BoardViewControl = TopToolbar
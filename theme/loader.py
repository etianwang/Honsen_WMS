"""Global theme loader for Honsen WMS."""

import os
import sys

_COMBO_MAX_VISIBLE = 12
_COMBO_MIN_VISIBLE = 6
_COMBO_ITEM_HEIGHT = 32


def _theme_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "theme")
    return os.path.dirname(os.path.abspath(__file__))


def load_stylesheet() -> str:
    theme_path = os.path.join(_theme_dir(), "theme.qss")
    with open(theme_path, "r", encoding="utf-8") as f:
        return f.read()


def configure_combo_box(
    combo,
    max_visible: int = _COMBO_MAX_VISIBLE,
    min_visible: int = _COMBO_MIN_VISIBLE,
) -> None:
    """Ensure dropdown lists show enough options at once."""
    combo.setMaxVisibleItems(max(max_visible, min_visible))
    view = combo.view()
    if view is not None:
        view.setSpacing(0)
        min_height = min_visible * _COMBO_ITEM_HEIGHT + 4
        view.setMinimumHeight(min_height)


def _patch_combo_boxes() -> None:
    """Apply sensible dropdown defaults to every QComboBox in the app."""
    from PyQt6.QtWidgets import QComboBox

    if getattr(QComboBox, "_wms_theme_patched", False):
        return

    original_init = QComboBox.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        configure_combo_box(self)

    QComboBox.__init__ = patched_init
    QComboBox._wms_theme_patched = True


def setup_app_theme(app) -> None:
    """Apply Fusion style and global QSS to the application."""
    _patch_combo_boxes()
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())


def apply_widget_role(widget, role: str) -> None:
    """Assign a semantic style role and refresh widget polish."""
    widget.setProperty("role", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)

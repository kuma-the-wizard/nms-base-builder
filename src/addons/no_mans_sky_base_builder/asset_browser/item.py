import json
import os

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

from functools import partial

import asset_browser.icons.icons

THUMB_SIZE = 48
ITEM_SIZE = 80
FONT_SIZE = 7

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
ICON_PATH = os.path.join(FILE_DIR, "icons")


class Thumb(QtWidgets.QLabel):
    def __init__(self, part_id=None, *args, **kwargs):
        super(Thumb, self).__init__(*args, **kwargs)
        part_id = part_id or ""
        icon_path = ":{}".format(part_id)
        if QtCore.QFile.exists(icon_path):
            pixmap = QtGui.QPixmap(icon_path)
            scaled = pixmap.scaled(
                THUMB_SIZE,
                THUMB_SIZE,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            self.setPixmap(scaled)
        self.setMinimumSize(QtCore.QSize(THUMB_SIZE, THUMB_SIZE))
        self.setMaximumSize(QtCore.QSize(THUMB_SIZE, THUMB_SIZE))
        self.setAlignment(QtCore.Qt.AlignCenter)


class Item(QtWidgets.QFrame):

    clicked = QtCore.Signal()
    varClicked = QtCore.Signal(str)

    def __init__(self, item_id=None, label=None, variants=None, *args, **kwargs):
        super(Item, self).__init__(*args, **kwargs)
        self.label = label or ""
        self.item_id = item_id or ""
        self.variants = variants or []
        self.setToolTip(self.item_id)
        self.setMinimumSize(QtCore.QSize(ITEM_SIZE, ITEM_SIZE))
        self.setMaximumSize(QtCore.QSize(ITEM_SIZE, ITEM_SIZE))
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        self._build_ui()
        self._layout()
        self._setup()
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def _build_ui(self):
        self.thumb = Thumb(part_id=self.item_id, parent=self)
        self.label_widget = QtWidgets.QLabel(self.label, parent=self)
        self.label_widget.setAlignment(QtCore.Qt.AlignCenter)
        self.label_widget.setWordWrap(True)
        font = QtGui.QFont("Decorative", FONT_SIZE)
        self.label_widget.setFont(font)
        self.label_widget.setMinimumWidth(THUMB_SIZE)
        self.label_widget.setMaximumWidth(THUMB_SIZE)
        self.variants_button = QtWidgets.QPushButton("v", self)
        self.variants_button.setContentsMargins(0, 0, 0, 0)
        var_but_width = 23
        self.variants_button.setGeometry(
            ITEM_SIZE - var_but_width - 2, 2, var_but_width, 23
        )
        self.variants_button.setVisible(False)

    def _layout(self):
        self.main_layout.addWidget(self.thumb, QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(self.label_widget, QtCore.Qt.AlignCenter)

    def _setup(self):
        self.variants_button.clicked.connect(self.open_context_menu)

    def open_context_menu(self):
        variants_menu = QtWidgets.QMenu(self.variants_button)
        action = variants_menu.addAction(self.label)
        action.triggered.connect(partial(self.add_part, self.item_id))
        for variant_id, variant_label in self.variants:
            action = variants_menu.addAction(variant_label)
            action.triggered.connect(partial(self.add_part, variant_id))
        variants_menu.exec(QtGui.QCursor.pos())

    def mousePressEvent(self, event):
        self.clicked.emit()

    def add_variant(self, variant_id, variant_label):
        self.variants.append((variant_id, variant_label))
        self.refresh_variants()

    def refresh_variants(self):
        if self.variants:
            self.variants_button.setVisible(True)

    def add_part(self, part_id):
        self.varClicked.emit(part_id)


class Preset(QtWidgets.QFrame):

    clicked = QtCore.Signal()
    editClicked = QtCore.Signal()

    def __init__(self, item_id=None, label=None, *args, **kwargs):
        super(Preset, self).__init__(*args, **kwargs)
        self.label = label or ""
        self.item_id = item_id or ""
        self.setToolTip(self.item_id)
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        self._build_ui()
        self._layout()
        self._setup_ui()
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def _build_ui(self):
        self.label_button = QtWidgets.QPushButton(self.label, parent=self)
        self.label_button.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        font = QtGui.QFont("Decorative", 10)
        self.label_button.setFont(font)
        self.edit_button = QtWidgets.QPushButton("Edit", parent=self)

    def _layout(self):
        self.main_layout.addWidget(self.label_button)
        self.main_layout.addWidget(self.edit_button)

    def _setup_ui(self):
        self.label_button.clicked.connect(self.clicked.emit)
        self.edit_button.clicked.connect(self.editClicked.emit)

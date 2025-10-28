import ctypes
import json
import os
import sys
import tempfile
import time
from functools import partial

import yaml

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

import yaml

import asset_browser.icons.icons
from asset_browser.collapsable_frame import CollapsableFrame
from asset_browser.flow_layout import FlowLayout
from asset_browser.item import Item, Preset
from asset_browser.utils import contexts, parts_definition

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
SEND_SNIPPET = os.path.join(FILE_DIR, "build_part_snippet.txt")
EDIT_PRESET_SNIPPET = os.path.join(FILE_DIR, "edit_preset_snippet.txt")
END_SNIPPET = os.path.join(FILE_DIR, "terminate_snippet.txt")
BROWSER_LAYOUT_FILE = os.path.join(FILE_DIR, "..", "resources", "asset_data.yaml")
NICE_NAMES_FILE = os.path.join(FILE_DIR, "..", "resources", "nice_names.json")
STYLESHEET_FILE = os.path.join(FILE_DIR, "core.css")
APP_ICON = os.path.join(FILE_DIR, "logo.png")
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
PRESET_PATH = os.path.join(USER_PATH, "presets")
COMMAND_FILE = os.path.join(FILE_DIR, "send_command.py")

with open(NICE_NAMES_FILE, "r") as stream:
    NICE_NAME_DATA = json.load(stream)


class AssetBrowser(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(AssetBrowser, self).__init__(*args, **kwargs)
        self.setWindowTitle("No Man's Sky Base Builder :: Asset Browser")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        app_id = "djmonkey.NMSBB.AssetBrowser.1"  # arbitrary string
        # FIXME: do this in some platform-agnostic way if possible
        if hasattr(ctypes, "windll"):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        self.setWindowTitle("No Man's Sky Blender Builder - Asset Browser")
        self.setWindowIcon(QtGui.QIcon(APP_ICON))
        self.__item_widgets = {}
        self.__search_buttons = {}
        self.__preset_search_buttons = {}
        self._build_ui()
        self._layout_ui()
        self._setup_ui()

        self.generate_contents()
        self.apply_style()

    def _build_ui(self):
        # Main
        self.main_widget = QtWidgets.QFrame(self)
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # Search
        self.top_bar_frame = QtWidgets.QFrame(self)
        self.top_bar_layout = QtWidgets.QHBoxLayout(self.top_bar_frame)
        self.top_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.search_lineedit = QtWidgets.QLineEdit(self.top_bar_frame)
        self.search_lineedit.setPlaceholderText("Search...")
        self.refresh_presets_button = QtWidgets.QPushButton(self.top_bar_frame)
        self.refresh_presets_button.setIcon(QtGui.QIcon(":TOP_BAR_REFRESH"))
        self.refresh_presets_button.setObjectName("refresh_button")
        self.refresh_presets_button.setCursor(
            QtGui.QCursor(QtCore.Qt.PointingHandCursor)
        )
        self.refresh_presets_button.setToolTip("Refresh Presets")

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget(self.main_widget)

        self.search_scroll = QtWidgets.QScrollArea(self.main_widget)
        self.search_scroll.setWidgetResizable(True)
        self.search_scroll.setVisible(False)

        self.search_tab_widget = QtWidgets.QTabWidget(self.search_scroll)
        self.search_scroll.setWidget(self.search_tab_widget)

        # Search Parts
        self.search_parts_scroll = QtWidgets.QScrollArea(self.search_tab_widget)
        self.search_parts_scroll.setWidgetResizable(True)
        self.search_parts_frame = QtWidgets.QFrame(self.search_parts_scroll)
        self.search_frame_layout = FlowLayout(parent=self.search_parts_frame)
        self.search_parts_scroll.setWidget(self.search_parts_frame)
        self.search_tab_widget.addTab(self.search_parts_scroll, "Parts")

        # Search presets
        self.search_presets_scroll = QtWidgets.QScrollArea(self.search_tab_widget)
        self.search_presets_scroll.setWidgetResizable(True)
        self.search_presets_frame = QtWidgets.QFrame(self.search_presets_scroll)
        self.search_presets_layout = QtWidgets.QVBoxLayout(self.search_presets_frame)
        self.search_presets_layout.setAlignment(QtCore.Qt.AlignTop)
        self.search_presets_scroll.setWidget(self.search_presets_frame)
        self.search_tab_widget.addTab(self.search_presets_scroll, "Presets")

    def refresh_search(self):
        with contexts.block_render(self):
            with contexts.WaitCursor():
                search = self.search_lineedit.text().lower()
                if not search or len(search) <= 2:
                    self.tab_widget.setVisible(True)
                    self.search_scroll.setVisible(False)
                    return
                self.tab_widget.setVisible(False)
                self.search_scroll.setVisible(True)
                for data_pack in [self.__search_buttons, self.__preset_search_buttons]:
                    for button_data in data_pack.values():
                        match = (
                            search in button_data["search_id"]
                            or search in button_data["search_label"]
                        )
                        button_data["widget"].setVisible(match)

    def generate_contents(self):
        browser_data = parts_definition.get_part_definition()
        # Add Categories
        for category_title, category_data in browser_data.items():

            # Main Category
            scroll_frame = QtWidgets.QScrollArea(self)
            scroll_frame.setWidgetResizable(True)
            frame = QtWidgets.QFrame(scroll_frame)
            scroll_frame.setWidget(frame)
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setAlignment(QtCore.Qt.AlignTop)
            self.tab_widget.addTab(scroll_frame, category_title)
            if not category_data:
                continue

            # Sub Categories
            for sub_category_title, items in category_data.items():
                title_label = CollapsableFrame(label=sub_category_title, parent=frame)
                layout.addWidget(title_label)
                if not items:
                    continue
                for item_data in items:
                    item = item_data["id"]
                    show_in_drawer = item_data["showInDrawer"]
                    nice_name = item_data["nice_name"]
                    if show_in_drawer == "True":
                        if isinstance(item, str):
                            # Add to tab.
                            item_widget = Item(
                                item_id=item,
                                label=nice_name,
                                parent=title_label,
                            )
                            title_label.addWidget(item_widget)
                            item_widget.clicked.connect(
                                partial(self.send_part_command_to_blender, item)
                            )
                            item_widget.varClicked.connect(
                                self.send_part_command_to_blender
                            )

                            # Add to search frame.
                            search_item_widget = Item(
                                item_id=item,
                                label=nice_name,
                                parent=title_label,
                            )
                            self.search_frame_layout.addWidget(search_item_widget)
                            search_item_widget.clicked.connect(
                                partial(self.send_part_command_to_blender, item)
                            )
                            search_item_widget.varClicked.connect(
                                self.send_part_command_to_blender
                            )
                            self.__search_buttons[item] = {
                                "widget": search_item_widget,
                                "search_id": item.lower(),
                                "search_label": nice_name.lower(),
                            }
                            self.__item_widgets[item] = [
                                item_widget,
                                search_item_widget,
                            ]

        # Add Variants
        for category_title, category_data in browser_data.items():
            if not category_data:
                continue
            # Sub Categories
            for sub_category_title, items in category_data.items():
                for item_data in items:
                    item = item_data["id"]
                    nice_name = item_data["nice_name"]
                    variant_of = item_data["variantOf"]
                    if variant_of != "None":
                        variant_key = variant_of[1:]
                        if variant_key in self.__item_widgets:
                            widgets = self.__item_widgets[variant_key]
                            for widget in widgets:
                                widget.add_variant(item, nice_name)

        # Add Presets.
        scroll_frame = QtWidgets.QScrollArea(self)
        scroll_frame.setWidgetResizable(True)
        self.presets_frame = QtWidgets.QFrame(scroll_frame)
        scroll_frame.setWidget(self.presets_frame)
        self.presets_layout = QtWidgets.QVBoxLayout(self.presets_frame)
        self.presets_layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab_widget.addTab(scroll_frame, "Presets")
        self.generate_presets()

    def clear_presets(self):
        for preset_id, preset_data in self.__preset_search_buttons.items():
            widget = preset_data["widget"]
            widget.parent().layout().removeWidget(widget)
            widget.deleteLater()
        for _ in range(self.presets_layout.count()):
            item = self.presets_layout.itemAt(0)
            widget = item.widget()
            if widget and isinstance(widget, CollapsableFrame):
                self.presets_layout.removeWidget(widget)
                widget.deleteLater()
        self.__preset_search_buttons = {}

    def generate_presets(self):
        self.__preset_search_buttons = {}
        # Add Categories.
        categories = sorted(os.listdir(PRESET_PATH))
        for category in categories:
            full_path = os.path.join(PRESET_PATH, category)
            if os.path.isdir(full_path):
                preset_category_frame = CollapsableFrame(
                    label=category, layout="vertical", parent=self.presets_frame
                )
                self.presets_layout.addWidget(preset_category_frame)
                presets = os.listdir(full_path)
                for preset in presets:
                    self.add_preset_to_frame(preset, preset_category_frame)

        # Add un-categorized presets.
        presets = sorted(os.listdir(PRESET_PATH))
        presets = [
            item for item in presets if os.path.isfile(os.path.join(PRESET_PATH, item))
        ]
        if presets:
            preset_category_frame = CollapsableFrame(
                label="Uncategorized Presets",
                layout="vertical",
                parent=self.presets_frame,
            )
            self.presets_layout.addWidget(preset_category_frame)
            for preset in presets:
                self.add_preset_to_frame(preset, preset_category_frame)

    def add_preset_to_frame(self, preset, frame):
        item_id = preset.split(".")[0]
        if not item_id:
            return
        nice_label = item_id.replace("_", " ").title()
        # Add preset
        item_widget = Preset(item_id=item_id, label=nice_label, parent=frame)
        frame.addWidget(item_widget)
        item_widget.clicked.connect(partial(self.send_part_command_to_blender, item_id))
        item_widget.editClicked.connect(
            partial(self.send_edit_preset_command_to_blender, item_id)
        )
        # Add to search
        search_item_widget = Preset(
            item_id=item_id, label=nice_label, parent=self.search_presets_frame
        )
        self.search_presets_layout.addWidget(search_item_widget)
        search_item_widget.clicked.connect(
            partial(self.send_part_command_to_blender, item_id)
        )
        search_item_widget.editClicked.connect(
            partial(self.send_edit_preset_command_to_blender, item_id)
        )
        self.__preset_search_buttons[item_id] = {
            "widget": search_item_widget,
            "search_id": item_id,
            "search_label": nice_label,
        }

    def _layout_ui(self):
        self.setCentralWidget(self.main_widget)
        self.main_layout.addWidget(self.top_bar_frame)
        self.top_bar_layout.addWidget(self.search_lineedit)
        self.top_bar_layout.addWidget(self.refresh_presets_button)
        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(self.search_scroll)

    def _setup_ui(self):
        self.search_lineedit.textChanged.connect(self.refresh_search)
        self.refresh_presets_button.clicked.connect(self.refresh_presets)
        self.tab_widget.currentChanged.connect(self.refresh_layouts)

    def refresh_layouts(self, tab_index):
        scroll_widget = self.tab_widget.currentWidget()
        widget = scroll_widget.widget()
        layout = widget.layout()
        for idx in range(layout.count()):
            frame_item = layout.itemAt(idx)
            frame = frame_item.widget()
            if isinstance(frame, CollapsableFrame):
                frame.inner_frame_layout.update()

    def refresh_presets(self):
        self.clear_presets()
        self.generate_presets()
        self.refresh_search()

    def apply_style(self):
        with open(STYLESHEET_FILE) as stream:
            self.setStyleSheet(stream.read())

    def send_part_command_to_blender(self, item_id):
        PYTHON_FILE = (
            COMMAND_FILE  # os.path.join(tempfile.gettempdir(), "command_script.py")
        )
        print(PYTHON_FILE)

        script_contents = ""
        with open(SEND_SNIPPET, "r") as stream:
            script_contents = stream.read()

        script_contents = script_contents.replace(
            "%PATH%",
            os.path.realpath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            ).replace("\\", "/"),
        )

        with open(PYTHON_FILE, "w") as stream:
            stream.write(script_contents.format(item_id))

        TEMP_PATH = os.path.join(tempfile.gettempdir(), "bpy_external.io")
        with open(TEMP_PATH, "w") as stream:
            stream.write(PYTHON_FILE)

    def send_edit_preset_command_to_blender(self, item_id):
        PYTHON_FILE = os.path.join(tempfile.gettempdir(), "command_script.py")

        script_contents = ""
        with open(EDIT_PRESET_SNIPPET, "r") as stream:
            script_contents = stream.read()

        script_contents = script_contents.replace(
            "%PATH%",
            os.path.realpath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            ).replace("\\", "/"),
        )

        with open(PYTHON_FILE, "w") as stream:
            stream.write(script_contents.format(item_id))

        TEMP_PATH = os.path.join(tempfile.gettempdir(), "bpy_external.io")
        with open(TEMP_PATH, "w") as stream:
            stream.write(PYTHON_FILE)

    def sizeHint(self):
        return QtCore.QSize(1000, 1000)

    def closeEvent(self, event):
        PYTHON_FILE = os.path.join(tempfile.gettempdir(), "command_script.py")
        script_contents = ""
        with open(END_SNIPPET, "r") as stream:
            script_contents = stream.read()
        with open(PYTHON_FILE, "w") as stream:
            stream.write(script_contents)

        TEMP_PATH = os.path.join(tempfile.gettempdir(), "bpy_external.io")
        with open(TEMP_PATH, "w") as stream:
            stream.write(PYTHON_FILE)

        time.sleep(0.5)
        with open(TEMP_PATH, "w") as stream:
            stream.write("")

        # Close
        super(AssetBrowser, self).closeEvent(event)


def load():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AssetBrowser()
    window.show()
    app.exit(app.exec_())

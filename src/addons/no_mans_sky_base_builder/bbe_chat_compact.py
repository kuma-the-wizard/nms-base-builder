"""Compact, edge-attached Messenger window behavior. No chat network work here."""
import ctypes
import html
import json
import os
from ctypes import wintypes
import sys
import time
from PySide6 import QtCore, QtGui, QtWidgets
import bbe_chat_state as chat_state


def windows_api():
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint)
    api.SetWindowPos.restype = wintypes.BOOL
    api.GetAncestor.argtypes = (wintypes.HWND, ctypes.c_uint)
    api.GetAncestor.restype = wintypes.HWND
    api.GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
    api.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    api.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    api.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    api.IsWindowVisible.argtypes = (wintypes.HWND,)
    api.IsIconic.argtypes = (wintypes.HWND,)
    return api


class ElidedLabel(QtWidgets.QLabel):
    def display_text(self):
        return self.fontMetrics().elidedText(self.text(), QtCore.Qt.ElideRight, self.contentsRect().width())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.WindowText))
        painter.drawText(self.contentsRect(), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.display_text())


class PeopleButton(QtWidgets.QToolButton):
    """A geometric chevron stays centered independently of font baselines."""
    def paintEvent(self, event):
        option = QtWidgets.QStyleOptionToolButton()
        self.initStyleOption(option)
        option.text = ''
        painter = QtWidgets.QStylePainter(self)
        painter.drawComplexControl(QtWidgets.QStyle.CC_ToolButton, option)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(self.palette().color(QtGui.QPalette.ButtonText), 2,
                                 QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        center = QtCore.QPointF(self.width()/2, self.height()/2)
        direction = -1 if self.text() == '‹' else 1
        path = QtGui.QPainterPath(center + QtCore.QPointF(-direction*2, -4))
        path.lineTo(center + QtCore.QPointF(direction*2, 0))
        path.lineTo(center + QtCore.QPointF(-direction*2, 4))
        painter.drawPath(path)


class CompactMessengerMixin:
    def _init_compact(self):
        self.collapsed = False
        self.dock_mode = 'floating'
        self._mini_size = QtCore.QSize(340, 300)
        self._away_since = None
        self._drag_point = None
        self._seen_inbox = None
        self.unread = {}
        self._pin_explicit = False
        self._closing = False
        self._toolbar_anchor = None
        QtWidgets.QApplication.instance().applicationStateChanged.connect(self._dropdown_state_changed)
        self.drawer = QtWidgets.QDialog(self, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.drawer.setObjectName('peopleDrawer')
        self.drawer.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.drawer.setWindowTitle('Users and conversations')
        self.drawer.setLayout(QtWidgets.QVBoxLayout())
        self.drawer.layout().setContentsMargins(8, 0, 8, 0)
        self.drawer.resize(248, 420)
        self._last_received = None
        self.mini_title = ElidedLabel('Main Room')
        self.mini_title.setToolTip('Drag to move; click to expand. New messages appear here.')
        self.mini_title.setMinimumWidth(60)
        self.mini_title.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.mini_title.installEventFilter(self)
        self.header_layout.insertWidget(0, self.mini_title, 1)
        self.people_gap = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.header_layout.insertSpacerItem(0, self.people_gap)
        self.people_button = PeopleButton(self.centralWidget())
        self.people_button.setObjectName('peopleHandle')
        self.people_button.setAccessibleName('Show users and conversations')
        self.people_button.setText('‹')
        self.people_button.setToolTip('Online users and direct messages')
        self.people_button.clicked.connect(lambda: self.sidebar_action.setChecked(not self.sidebar_action.isChecked()))
        self.people_button.setFixedSize(24, 56)
        self.collapse_button = QtWidgets.QToolButton()
        self.collapse_button.setText('−')
        self.collapse_button.setToolTip('Collapse to chat strip')
        self.collapse_button.clicked.connect(lambda: self._collapse(not self.collapsed))
        self.header_layout.addWidget(self.collapse_button)
        self.grip = QtWidgets.QSizeGrip(self)
        self.main_layout.addWidget(self.grip, 0, QtCore.Qt.AlignRight)
        for widget in (self.mini_title, self.people_button, self.collapse_button, self.grip):
            widget.hide()
        self.compact_timer = QtCore.QTimer(self)
        self.compact_timer.timeout.connect(self._compact_tick)
        self.compact_timer.start(500)

    def _set_pin(self, enabled):
        self._pin_explicit = True
        geometry = self.geometry()
        for control in (self.pin_button, self.pin_action):
            control.blockSignals(True)
            control.setChecked(enabled)
            control.blockSignals(False)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, enabled)
        self.show()
        self.setGeometry(geometry)
        self._native_pin(force=True)

    def _native_pin(self, force=False):
        if sys.platform != 'win32' or QtWidgets.QApplication.platformName() == 'offscreen':
            return True
        api = windows_api()
        hwnd = api.GetAncestor(int(self.winId()), 2) or int(self.winId())
        enabled = self.pin_button.isChecked()
        if not force and bool(api.GetWindowLongPtrW(hwnd, -20) & 0x8) == enabled:
            return True
        # HWND_TOPMOST / HWND_NOTOPMOST, preserving position, size and keyboard focus.
        ok = api.SetWindowPos(hwnd, -1 if enabled else -2, 0, 0, 0, 0, 0x0013)
        actual = bool(api.GetWindowLongPtrW(hwnd, -20) & 0x8)
        if not ok or actual != enabled:
            self.status.setText('Windows could not apply Always on top. Toggle it to retry.')
            return False
        return True

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'pin_button'):
            QtCore.QTimer.singleShot(0, self._native_pin)

    def _set_sidebar(self, visible):
        if self.mini and hasattr(self, 'drawer'):
            self.drawer.layout().addWidget(self.sidebar)
            self.sidebar.layout().setStretchFactor(self.rooms, 0)
            self.sidebar.layout().setStretchFactor(self.online_users, 1)
            self.sidebar.show()
            if visible:
                self._collapse(False)
                self._position_drawer()
                self.drawer.show()
                self.drawer.raise_()
            else:
                self.drawer.hide()
            self._layout_people_handle()
        else:
            if hasattr(self, 'drawer'):
                self.drawer.hide()
            self.centralWidget().layout().insertWidget(0, self.sidebar)
            self.sidebar.layout().setStretchFactor(self.rooms, 0)
            self.sidebar.layout().setStretchFactor(self.online_users, 1)
            self.sidebar.setVisible(visible)

    def _set_mini(self, enabled):
        if not hasattr(self, 'drawer'):
            return
        self._collapse(False)
        if enabled and not self.mini:
            self._full_size = self.size()
        if not enabled and self.mini:
            self._mini_size = self.size()
        self.mini = enabled
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, enabled)
        self.show()
        self.sidebar_action.setChecked(not enabled)
        self._set_sidebar(not enabled)
        for widget in (*self.header_extras, self.heading, self.tools_widget, self.send_widget):
            widget.setVisible(not enabled)
        for widget in (self.mini_title, self.people_button, self.collapse_button, self.grip):
            widget.setVisible(enabled)
        self.main_layout.setContentsMargins(*( (7, 3, 7, 5) if enabled else (18, 13, 18, 12)))
        self.history_region.layout().setContentsMargins(24 if enabled else 0, 0, 0, 0)
        self._update_window_shape()
        self.main_layout.setSpacing(3 if enabled else 10)
        self.composer.setFixedHeight(42 if enabled else 75)
        self.composer.setPlaceholderText('Message…' if enabled else 'Write a message. Enter sends; Shift+Enter makes a new line.')
        self.setMinimumSize(280 if enabled else 320, 180 if enabled else 260)
        self._update_status_visibility()
        self._draw_messages()
        self.resize(self._mini_size if enabled else self._full_size)
        self._native_pin()
        self._layout_people_handle()
        self._place_attached()

    def _collapse(self, collapsed):
        if not self.mini or self.collapsed == collapsed:
            return
        if collapsed:
            self._mini_size = self.size()
            self.sidebar_action.setChecked(False)
        self.collapsed = collapsed
        self.collapse_button.setText('+' if collapsed else '−')
        self.collapse_button.setToolTip('Expand chat' if collapsed else 'Collapse to chat strip')
        for widget in (self.history_region, self.composer_row, self.grip):
            widget.setVisible(not collapsed)
        self.preview.setVisible(not collapsed and self.pending is not None)
        self.status.setVisible(not collapsed and self.status.text() not in ('Connected', 'Sent', 'Connecting...', ''))
        self.main_layout.setContentsMargins(*( (5, 1, 5, 1) if collapsed else (7, 3, 7, 5)))
        self.people_gap.changeSize(25 if collapsed else 0, 0, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.header_layout.invalidate()
        height = self._strip_height()
        for button in (self.options_button, self.collapse_button):
            button.setFixedHeight(max(18, height-4) if collapsed else 24)
        self.setMinimumSize(280, height if collapsed else 180)
        self.resize(self.width(), height if collapsed else self._mini_size.height())
        self._update_badge()
        self._update_window_shape()
        if not collapsed:
            self._away_since = None
        self._layout_people_handle()
        self._place_attached()
        if collapsed and self.dock_mode == 'toolbar' and self._settings().get('native_chat_toolbar'):
            self.hide()

    def _layout_people_handle(self):
        if not hasattr(self, "people_button"):
            return
        height = min(22, self.height()-4) if self.collapsed else 48
        self.people_button.setFixedSize(22, height)
        if self.collapsed:
            y = (self.centralWidget().height()-height)//2
        else:
            y = (self.centralWidget().height()-height)//2
        self.people_button.move(5, max(2, y))
        self.people_button.raise_()
        left = self._drawer_on_left()
        self.people_button.setText(("›" if left else "‹") if self.drawer.isVisible() else ("‹" if left else "›"))
        self.people_button.setToolTip("Hide users and conversations" if self.drawer.isVisible() else "Online users, rooms and direct messages")

    def _update_window_shape(self):
        if not self.mini:
            self.clearMask()
            return
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect()), 9, 9)
        self.setMask(QtGui.QRegion(path.toFillPolygon().toPolygon()))

    def _toolbar_bounds(self):
        bounds = self._blender_bounds()
        row = self._settings().get('chat_toolbar')
        if (isinstance(row, list) and len(row) == 4 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in row)
                and row[2] > 0 and row[3] > 0):
            x,y,w,h = row
            return QtCore.QRect(bounds.x()+round(x*bounds.width()), bounds.y()+round(y*bounds.height()),
                                round(w*bounds.width()), round(h*bounds.height())).intersected(bounds)
        viewport = self._viewport_bounds()
        return QtCore.QRect(viewport.x(), viewport.y()-26, viewport.width(), 26)

    def _strip_height(self):
        return max(22, min(36, self._toolbar_bounds().height()-2)) if self.dock_mode == 'toolbar' else 26

    def _drawer_on_left(self):
        bounds = (self.screen() or QtWidgets.QApplication.primaryScreen()).availableGeometry()
        return self.x()-self.drawer.width() >= bounds.left()

    def _blender_bounds(self):
        screen = self.screen() or QtWidgets.QApplication.primaryScreen()
        fallback = screen.availableGeometry()
        pid = self._settings().get('blender_pid')
        if not pid or sys.platform != 'win32' or QtWidgets.QApplication.platformName() == 'offscreen':
            return fallback
        api = windows_api()
        api.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
        api.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
        rectangles = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        @callback_type
        def visit(hwnd, _):
            process = wintypes.DWORD()
            api.GetWindowThreadProcessId(hwnd, ctypes.byref(process))
            if process.value == pid and api.IsWindowVisible(hwnd) and not api.IsIconic(hwnd):
                r = wintypes.RECT()
                origin = wintypes.POINT(0, 0)
                if api.GetClientRect(hwnd, ctypes.byref(r)) and api.ClientToScreen(hwnd, ctypes.byref(origin)) and r.right > 400 and r.bottom > 250:
                    rectangles.append((hwnd, QtCore.QRect(origin.x, origin.y, r.right, r.bottom)))
            return True
        api.EnumWindows.argtypes = (callback_type, wintypes.LPARAM)
        api.EnumWindows(visit, 0)
        if not rectangles:
            return fallback
        preferred = (self._toolbar_anchor or {}).get('hwnd')
        hwnd, rect = next((item for item in rectangles if item[0] == preferred),
                         max(rectangles, key=lambda item: item[1].width()*item[1].height()))
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.DWORD), ('monitor', wintypes.RECT),
                        ('work', wintypes.RECT), ('flags', wintypes.DWORD), ('device', wintypes.WCHAR * 32)]
        api.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
        api.MonitorFromWindow.restype = wintypes.HANDLE
        api.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if api.GetMonitorInfoW(api.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
            screens = QtWidgets.QApplication.screens()
            # Qt 6 can expose a friendly monitor name ("KB272 E") rather than
            # Windows' DISPLAY2 ID. Match its native origin and scaled size too.
            def monitor_distance(display):
                g, ratio = display.geometry(), display.devicePixelRatio()
                return (abs(g.x()-info.monitor.left)+abs(g.y()-info.monitor.top)
                        +abs(round(g.width()*ratio)-(info.monitor.right-info.monitor.left))
                        +abs(round(g.height()*ratio)-(info.monitor.bottom-info.monitor.top)))
            display = next((s for s in screens if s.name() == info.device), None)
            if display is None and screens:
                display = min(screens, key=monitor_distance)
            if display is not None:
                ratio, g = display.devicePixelRatio(), display.geometry()
                return QtCore.QRect(g.x()+round((rect.x()-info.monitor.left)/ratio),
                                    g.y()+round((rect.y()-info.monitor.top)/ratio),
                                    round(rect.width()/ratio), round(rect.height()/ratio))
        return fallback

    def _viewport_bounds(self):
        bounds = self._blender_bounds()
        viewport = self._settings().get('chat_viewport')
        if (isinstance(viewport, list) and len(viewport) == 4
                and all(isinstance(n, (int, float)) and 0 <= n <= 1 for n in viewport)
                and viewport[2] > 0 and viewport[3] > 0):
            x, y, w, h = viewport
            return QtCore.QRect(bounds.x()+round(x*bounds.width()), bounds.y()+round(y*bounds.height()),
                                round(w*bounds.width()), round(h*bounds.height())).intersected(bounds)
        return bounds.adjusted(0, 70, 0, -24)

    def _dock(self, side):
        if side == 'floating':
            self.dock_mode = side
            return
        if side in ('left', 'right'):
            side = 'bottom-' + side
        self.mini_action.setChecked(True)
        self.dock_mode = side
        if side == 'toolbar':
            self._collapse(True)
        self._place_attached()

    def _place_attached(self):
        if not self.mini or self.dock_mode == 'floating':
            return
        if self.dock_mode == 'toolbar':
            row = self._toolbar_bounds()
            if self.collapsed:
                height = self._strip_height()
                self.setMinimumHeight(height)
                self.resize(self.width(), height)
            native = self._settings().get('native_chat_toolbar')
            anchor = self._toolbar_anchor if native else None
            if anchor:
                bounds = self._blender_bounds()
                x = bounds.left()+round(anchor['x']*bounds.width())-self.width()//2
                y = bounds.top()+round(anchor['bottom']*bounds.height())+2
                self.move(max(bounds.left()+4, min(x, bounds.right()-self.width()-4)),
                          max(bounds.top(), min(y, bounds.bottom()-self.height())))
            else:
                self.move(max(row.left()+4, row.right()-100-self.width()+1), row.bottom()+2 if native else row.top()+1)
            self._layout_people_handle()
            if self.drawer.isVisible():
                self._position_drawer()
            return
        bounds = self._viewport_bounds().adjusted(6, 6, -6, -6)
        if bounds.width() < 280 or bounds.height() < (32 if self.collapsed else 180):
            return
        if self.width() > bounds.width() or self.height() > bounds.height():
            self.resize(min(self.width(), bounds.width()), min(self.height(), bounds.height()))
        right = 'right' in self.dock_mode
        centered = self.dock_mode in ('top', 'bottom')
        top = self.dock_mode.startswith('top')
        x = bounds.center().x() - self.width()//2 if centered else (bounds.right()-self.width()+1 if right else bounds.left())
        y = bounds.top() if top else bounds.bottom()-self.height()+1
        if self.pos() != QtCore.QPoint(x, y):
            self.move(x, y)
        self._layout_people_handle()
        if self.drawer.isVisible():
            self._position_drawer()

    def _position_drawer(self):
        bounds = (self.screen() or QtWidgets.QApplication.primaryScreen()).availableGeometry()
        x = self.x()-self.drawer.width()+2 if self._drawer_on_left() else self.x()+self.width()-2
        y = self.y()
        # Keep the two top edges together; shorten the drawer near the screen
        # bottom instead of shifting it above the conversation.
        layout = self.sidebar.layout()
        margins = layout.contentsMargins()
        chrome = margins.top() + margins.bottom() + layout.spacing() * (layout.count()-1)
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() not in (self.rooms, self.online_users):
                chrome += item.sizeHint().height()
        rooms_height = max(1, min(8, self.rooms.count())) * max(26, self.rooms.sizeHintForRow(0)) + 4
        users_height = max(2, min(12, self.online_users.count())) * max(22, self.online_users.sizeHintForRow(0)) + 4
        height = min(max(320, chrome + rooms_height + users_height), 640, max(1, bounds.bottom()-y+1))
        # Share constrained space, so neither list can push the other off-screen.
        budget = max(0, height-chrome)
        self.rooms.setMaximumHeight(min(rooms_height, max(0, budget-min(users_height, budget//2))))
        self.drawer.resize(self.drawer.width(), height)
        self.drawer.move(max(bounds.left(), min(x, bounds.right()-self.drawer.width()+1)),
                         y)

    def _compact_tick(self):
        if self._closing:
            return
        self._consume_blender_command()
        self._publish_toolbar_status()
        enabled = self._settings().get('enabled') is True
        self.chat_enabled_toggle.blockSignals(True)
        self.chat_enabled_toggle.setChecked(enabled)
        self.chat_enabled_toggle.setEnabled(self._settings().get('online_access', True))
        self.chat_enabled_toggle.blockSignals(False)
        if self.mini and self.collapsed and self.dock_mode == 'toolbar' and self._settings().get('native_chat_toolbar'):
            self.hide()
        if self.pin_button.isChecked():
            self._native_pin()
        if not self.mini or not self.isVisible():
            return
        phase = chat_state.pulse_on(time.monotonic())
        if phase != getattr(self, '_title_pulse_phase', None):
            self._title_pulse_phase = phase
            self._update_badge()
        self._place_attached()
        point = QtGui.QCursor.pos()
        inside = self.frameGeometry().contains(point) or (self.drawer.isVisible() and self.drawer.frameGeometry().contains(point))
        busy = (self.isActiveWindow() and self.composer.hasFocus()) or self.sending or self.snapshot_id or self.drawer.isVisible()
        busy = busy or QtWidgets.QApplication.activeModalWidget() is not None or QtWidgets.QApplication.activePopupWidget() is not None
        if inside:
            self._collapse(False)
            self._away_since = None
        elif not busy:
            if self._away_since is None:
                self._away_since = time.monotonic()
            elif time.monotonic()-self._away_since > 1.2:
                self._collapse(True)
        else:
            self._away_since = None
        if self.isActiveWindow() and not self.collapsed:
            self.unread.pop(self.target or 'main', None)
            self._notifications.get('directed', {}).pop(self.target or 'main', None)
            self._update_badge()

    def eventFilter(self, watched, event):
        if (hasattr(self, 'scroll') and watched is self.scroll.viewport()
                and event.type() == QtCore.QEvent.Wheel):
            QtCore.QTimer.singleShot(0, self._user_scrolled)
        if watched is getattr(self, 'mini_title', None):
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self._drag_point = event.globalPosition().toPoint() - self.pos()
                self._collapse(False)
                return True
            if event.type() == QtCore.QEvent.MouseMove and self._drag_point is not None:
                self.dock_mode = 'floating'
                self.move(event.globalPosition().toPoint() - self._drag_point)
                return True
            if event.type() == QtCore.QEvent.MouseButtonRelease:
                self._drag_point = None
                return True
        return super().eventFilter(watched, event)

    def _remember_received(self, messages):
        chat_state.remember_received(self._notifications, messages, self.persona, self.names)
        self._last_received = chat_state.latest_received(self._notifications, self.target)

    def _update_badge(self):
        status = chat_state.toolbar(self._notifications, None)
        count = status['directed']
        self._last_received, _ = chat_state.bar_message(self._notifications)
        room = self.heading.text().replace('Direct Message · ', 'DM · ')
        if self.collapsed:
            latest = self._last_received
            if latest:
                text = chat_state.preview(latest)
                room = f"{latest.get('name', 'User')}: {text}"
            else:
                room = 'Waiting for messages'
        self.mini_title.setText(('● ' + str(count) + ' · ' if count else '') + room)
        self.mini_title.setStyleSheet('color: #ffbd66;' if count and chat_state.pulse_on(time.monotonic()) else '')
        self.mini_title.setToolTip('<qt>' + html.escape(room) + '<br>Drag to move · Click to expand</qt>')
        self.setWindowTitle(('(' + str(count) + ') ' if count else '') + 'BBE Messenger')

    def _consume_blender_command(self):
        path = self.snapshot_dir / 'messenger-command.json'
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            path.unlink(missing_ok=True)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict) or data.get('action') not in ('CHAT', 'PEOPLE', 'TOOLBAR'):
            return
        if data['action'] == 'TOOLBAR':
            target = data.get('target')
            if target is not None and (not isinstance(target, str) or len(target) > 64):
                return
            if target != self.target:
                if self.composer.toPlainText().strip() or self.pending:
                    self.status.setText('Finish or clear this draft before switching conversations.')
                else:
                    latest = chat_state.latest_received(self._notifications, target)
                    self._open_conversation(target, (latest or {}).get('name', 'User'))
            anchor = data.get('anchor')
            if (isinstance(anchor, dict) and all(isinstance(anchor.get(k), (int, float))
                    and 0 <= anchor[k] <= 1 for k in ('x', 'bottom'))):
                self._toolbar_anchor = anchor
            else:
                self._toolbar_anchor = None
            self.mini_action.setChecked(True)
            self.dock_mode = 'toolbar'
        self._collapse(False)
        self.showNormal()
        self._place_attached()
        self.raise_()
        self.activateWindow()
        if data['action'] == 'PEOPLE':
            self.sidebar_action.setChecked(True)
            self._set_sidebar(True)
        else:
            self.composer.setFocus()

    def _dropdown_state_changed(self, state):
        if state == QtCore.Qt.ApplicationInactive:
            QtCore.QTimer.singleShot(50, self._dismiss_dropdown_if_inactive)

    def _dismiss_dropdown_if_inactive(self):
        if (not self._closing and self.mini and self.dock_mode == 'toolbar'
                and self._settings().get('native_chat_toolbar') and not self.collapsed
                and not self.isActiveWindow() and not self.drawer.isActiveWindow()
                and QtWidgets.QApplication.activeModalWidget() is None
                and QtWidgets.QApplication.activePopupWidget() is None
                and not (self.account_dialog and self.account_dialog.isVisible())):
            self._collapse(True)

    def _publish_toolbar_status(self):
        if not self._settings().get('native_chat_toolbar'):
            return
        now = time.monotonic()
        fresh = (self._enabled() and now-getattr(self, '_online_synced_at', float('-inf')) < 30)
        online = len({p['id'] for p in self.online if p.get('id') and p['id'] != self.persona}) if fresh else None
        self._notifications.update(unread=self.unread)
        payload = chat_state.toolbar(self._notifications, online, self.target)
        if payload == getattr(self, '_published_toolbar', None) and now-getattr(self, '_published_at', 0) < 5:
            return
        try:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
            path = self.snapshot_dir / 'toolbar-status.json'
            temporary = path.with_suffix('.new')
            temporary.write_text(json.dumps(payload), encoding='utf-8')
            os.replace(temporary, path)
            self._published_toolbar, self._published_at = payload, now
            chat_state.save(self.snapshot_dir/'notifications.json', self._notifications)
        except OSError:
            pass

    def _notify_inbox(self, inbox):
        closed = self.closed_conversations.get(self.persona, {})
        reopened = False
        for message in inbox:
            sender = message.get('from')
            if sender in closed and message.get('to') == self.persona and message.get('time', 0) > closed[sender]:
                closed.pop(sender)
                reopened = True
        if reopened:
            chat_state.save(self.snapshot_dir/'closed-conversations.json', self.closed_conversations)
        viewed = (self.target or 'main') if not self.collapsed and self.isActiveWindow() else None
        before = sum(self.unread.values())
        chat_state.update(self._notifications, {'inbox': inbox, 'messages': self.messages}, self.persona, self.names, viewed)
        self.unread = self._notifications['unread']
        self._seen_inbox = self._notifications['seen']
        self._last_received = chat_state.latest_received(self._notifications, self.target)
        if sum(self.unread.values()) > before and not viewed:
            QtWidgets.QApplication.alert(self, 3000)
        self._update_badge()

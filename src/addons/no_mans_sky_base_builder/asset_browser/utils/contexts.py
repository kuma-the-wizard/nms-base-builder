from contextlib import contextmanager

from .qt import QtCore, QtGui, QtWidgets


@contextmanager
def block_render(widget):
    widget.setUpdatesEnabled(False)
    try:
        yield
    finally:
        widget.setUpdatesEnabled(True)


@contextmanager
def WaitCursor():
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
        yield
    finally:
        QtWidgets.QApplication.restoreOverrideCursor()

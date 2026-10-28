"""Keep the companion alive only while a connected Blender process is alive."""
import ctypes
import os
import sys

from PySide6 import QtCore


class ProcessHandle:
    def __init__(self, pid):
        self.pid = pid
        self.handle = None
        if sys.platform == 'win32':
            from ctypes import wintypes
            self.api = ctypes.WinDLL('kernel32', use_last_error=True)
            self.api.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            self.api.OpenProcess.restype = wintypes.HANDLE
            self.api.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
            self.api.WaitForSingleObject.restype = wintypes.DWORD
            self.api.CloseHandle.argtypes = (wintypes.HANDLE,)
            self.api.CloseHandle.restype = wintypes.BOOL
            # Retain a handle to the actual process: PID reuse cannot revive it.
            self.handle = self.api.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE

    def alive(self):
        if sys.platform == 'win32':
            return bool(self.handle) and self.api.WaitForSingleObject(self.handle, 0) == 258
        try:
            os.kill(self.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            pass
        return True

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


class BlenderLifetime(QtCore.QObject):
    ended = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.owners = {}
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.check)

    def add_owner(self, pid):
        if type(pid) is not int or not 0 < pid <= 0xffffffff:
            return False
        old = self.owners.get(pid)
        if old and old.alive():
            return True
        if old:
            old.close()
            del self.owners[pid]
        owner = ProcessHandle(pid)
        if not owner.alive():
            owner.close()
            return False
        self.owners[pid] = owner
        self.timer.start()
        return True

    def check(self):
        if not self.owners:
            return
        for pid, owner in list(self.owners.items()):
            if not owner.alive():
                owner.close()
                del self.owners[pid]
        if not self.owners:
            self.timer.stop()
            self.ended.emit()

    def close(self):
        self.timer.stop()
        for owner in self.owners.values():
            owner.close()
        self.owners.clear()

"""Test-only native VFS observation at the real rollback-journal deletion.

All other operations and encryption use the unchanged audited engine/VFS. No
replacement I/O, success codes, crypto mocks or simulated commit are supplied.
Installed only inside a disposable spawned child that is killed by the test.
"""
import ctypes
import signal


class _VFS(ctypes.Structure):
    _fields_ = [("iVersion", ctypes.c_int), ("szOsFile", ctypes.c_int),
                ("mxPathname", ctypes.c_int), ("pNext", ctypes.c_void_p),
                ("zName", ctypes.c_char_p), ("pAppData", ctypes.c_void_p)] + [
        (name, ctypes.c_void_p) for name in (
            "xOpen", "xDelete", "xAccess", "xFullPathname", "xDlOpen", "xDlError",
            "xDlSym", "xDlClose", "xRandomness", "xSleep", "xCurrentTime",
            "xGetLastError", "xCurrentTimeInt64", "xSetSystemCall", "xGetSystemCall", "xNextSystemCall")]


class SQLCipherCommitProbe:
    def __init__(self, provider, main, channel, boundary):
        self.library = ctypes.CDLL(provider._load_driver().__file__)
        self.library.sqlite3_vfs_find.argtypes = [ctypes.c_char_p]
        self.library.sqlite3_vfs_find.restype = ctypes.POINTER(_VFS)
        self.library.sqlite3_vfs_register.argtypes = [ctypes.POINTER(_VFS), ctypes.c_int]
        self.library.sqlite3_vfs_register.restype = ctypes.c_int
        original = self.library.sqlite3_vfs_find(None)
        if not original or original.contents.iVersion != 3:
            raise RuntimeError("native_vfs_contract_invalid")
        self.vfs = _VFS.from_buffer_copy(original.contents)
        self.vfs.zName = b"jkm-test-observed-real-commit"
        self.vfs.pNext = None
        delete_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(_VFS), ctypes.c_char_p, ctypes.c_int)
        original_delete = delete_type(original.contents.xDelete)
        self.armed = False
        expected = str(main).encode() + b"-journal"

        def delete(vfs, name, sync_dir):
            matched = self.armed and name == expected
            if matched and boundary == "vfs_before_journal_delete":
                channel.send((boundary, sync_dir))
                signal.pause()
            result = original_delete(original, name, sync_dir)
            if matched and boundary == "vfs_after_journal_delete":
                channel.send((boundary, sync_dir, result))
                signal.pause()
            return result

        self.callback = delete_type(delete)
        self.vfs.xDelete = ctypes.cast(self.callback, ctypes.c_void_p).value
        if self.library.sqlite3_vfs_register(ctypes.byref(self.vfs), 1) != 0:
            raise RuntimeError("native_vfs_registration_failed")

"""Return unused native heap pages on glibc hosts; harmless elsewhere."""
import ctypes
import gc
import sys


def release_unused_memory():
    if not sys.platform.startswith('linux'):
        return
    gc.collect()
    try:
        trim = ctypes.CDLL(None).malloc_trim
        trim.argtypes = [ctypes.c_size_t]
        trim.restype = ctypes.c_int
        trim(0)
    except (AttributeError, OSError):
        pass  # Other C libraries need not implement glibc's optional helper.

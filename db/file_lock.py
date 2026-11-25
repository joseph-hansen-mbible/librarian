import errno
import os
import time


if os.name == "nt":
    import msvcrt

    LOCK_SH = 1
    LOCK_EX = 2
    LOCK_NB = 4
    LOCK_UN = 8

    def flock(file_descriptor, operation):
        os.lseek(file_descriptor, 0, os.SEEK_SET)

        if operation & LOCK_UN:
            msvcrt.locking(file_descriptor, msvcrt.LK_UNLCK, 1)
            return

        if operation & LOCK_NB:
            try:
                msvcrt.locking(file_descriptor, msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise BlockingIOError(
                    errno.EACCES, "file is locked"
                ) from error
            return

        while True:
            try:
                msvcrt.locking(file_descriptor, msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.05)
else:
    import fcntl

    LOCK_SH = fcntl.LOCK_SH
    LOCK_EX = fcntl.LOCK_EX
    LOCK_NB = fcntl.LOCK_NB
    LOCK_UN = fcntl.LOCK_UN

    def flock(file_descriptor, operation):
        last_error = OSError("Flock retry exhausted")
        for attempt in range(5):
            try:
                fcntl.flock(file_descriptor, operation)
                return
            except OSError as error:
                last_error = error
                if error.errno not in (errno.EIO, errno.EAGAIN, errno.EACCES):
                    raise
                if operation & LOCK_NB and error.errno in (errno.EAGAIN, errno.EACCES):
                    raise BlockingIOError(errno.EACCES, "file is locked") from error
                if attempt < 4:
                    time.sleep((attempt + 1) * 0.05)
        raise last_error

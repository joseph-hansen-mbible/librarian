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
        fcntl.flock(file_descriptor, operation)

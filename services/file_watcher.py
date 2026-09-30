import os
import threading
import time

from .database import add_job
from .print_queue import submit_print


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

WATCH_FOLDER = os.path.join(
    BASE_DIR,
    "data",
    "to_print"
)


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt"
}


_seen = set()

_started = False


def _get_supported_files():

    if not os.path.exists(WATCH_FOLDER):
        os.makedirs(
            WATCH_FOLDER,
            exist_ok=True
        )

    files = []

    for name in os.listdir(WATCH_FOLDER):

        full_path = os.path.join(
            WATCH_FOLDER,
            name
        )

        if not os.path.isfile(full_path):
            continue

        extension = os.path.splitext(
            name
        )[1].lower()

        if extension in SUPPORTED_EXTENSIONS:
            files.append(
                os.path.abspath(full_path)
            )

    return files


def _process_file(file_path):

    printer = None

    try:

        from .printer_manager import get_default_printer

        printer = get_default_printer()

        if not printer:

            add_job(
                file_path,
                "No printer",
                1,
                "file",
                "Failed",
                "No default printer configured"
            )

            return

        # Small delay so that files copied into the folder
        # have time to finish writing.
        time.sleep(1)

        result = submit_print(
            file_path,
            printer,
            copies=1,
            paper_size="A4",
            orientation="Portrait",
            color_mode="Color",
            duplex=False
        )

        if result and result.get("ok"):

            add_job(
                file_path,
                printer,
                1,
                "file",
                "Success",
                None,
                "A4",
                "Portrait",
                "Color",
                False
            )

        else:

            error = (
                result.get("error")
                if result
                else "Unknown printing error"
            )

            add_job(
                file_path,
                printer,
                1,
                "file",
                "Failed",
                error,
                "A4",
                "Portrait",
                "Color",
                False
            )

    except Exception as e:

        add_job(
            file_path,
            printer or "Unknown",
            1,
            "file",
            "Failed",
            str(e),
            "A4",
            "Portrait",
            "Color",
            False
        )


def _watch_loop():

    global _seen

    # ---------------------------------------------------------
    # Important:
    # Existing files must NOT automatically print after restart.
    # ---------------------------------------------------------

    for file_path in _get_supported_files():

        _seen.add(file_path)

    while True:

        try:

            current_files = set(
                _get_supported_files()
            )

            new_files = current_files - _seen

            for file_path in sorted(new_files):

                _seen.add(file_path)

                threading.Thread(
                    target=_process_file,
                    args=(file_path,),
                    daemon=True
                ).start()

            # Remove files which no longer exist from memory.
            _seen.intersection_update(
                current_files
            )

        except Exception:
            pass

        time.sleep(2)


def start_watcher():

    global _started

    if _started:
        return

    _started = True

    thread = threading.Thread(
        target=_watch_loop,
        daemon=True,
        name="FileWatcher"
    )

    thread.start()
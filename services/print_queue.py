import queue
import threading

from .printer_manager import print_file


_job_queue = queue.Queue()

_worker_started = False

_active_jobs = 0

_lock = threading.Lock()


def _worker():

    global _active_jobs

    while True:

        job = _job_queue.get()

        if job is None:

            _job_queue.task_done()

            break

        try:

            with _lock:
                _active_jobs += 1

            result = print_file(
                job["file_path"],
                job["printer"],
                job["copies"],
                job["paper_size"],
                job["orientation"],
                job["color_mode"],
                job["duplex"]
            )

            job["result"] = result

        except Exception as e:

            job["result"] = {
                "ok": False,
                "error": str(e)
            }

        finally:

            with _lock:
                _active_jobs -= 1

            job["event"].set()

            _job_queue.task_done()


def start_queue():

    global _worker_started

    if _worker_started:
        return

    _worker_started = True

    worker = threading.Thread(
        target=_worker,
        daemon=True,
        name="PrintWorker"
    )

    worker.start()


def submit_print(
    file_path,
    printer,
    copies=1,
    paper_size="A4",
    orientation="Portrait",
    color_mode="Color",
    duplex=False
):

    start_queue()

    event = threading.Event()

    job = {
        "file_path": file_path,
        "printer": printer,
        "copies": copies,
        "paper_size": paper_size,
        "orientation": orientation,
        "color_mode": color_mode,
        "duplex": duplex,
        "event": event,
        "result": None
    }

    _job_queue.put(job)

    # Wait until this job has finished.
    event.wait()

    return job["result"]


def queue_status():

    with _lock:

        return {
            "waiting": _job_queue.qsize(),
            "printing": _active_jobs > 0,
            "active": _active_jobs
        }
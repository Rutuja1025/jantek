import os
import threading
import time
from datetime import datetime

from .database import list_schedules, add_job
from .print_queue import submit_print


_last_run = set()

_started = False


def _schedule_loop():

    while True:

        try:

            now = datetime.now()

            current_time = now.strftime("%H:%M")

            today = now.strftime("%A").lower()

            schedules = list_schedules()

            for schedule in schedules:

                if not schedule["enabled"]:
                    continue

                schedule_time = schedule["print_time"]

                if schedule_time != current_time:
                    continue

                days_text = (
                    schedule["days"]
                    .lower()
                    .strip()
                )

                # Supported values:
                # daily
                # monday,tuesday
                # monday
                if days_text != "daily":

                    selected_days = {
                        item.strip()
                        for item in days_text.split(",")
                    }

                    if today not in selected_days:
                        continue

                run_key = (
                    f"{schedule['id']}-"
                    f"{now.strftime('%Y-%m-%d')}-"
                    f"{current_time}"
                )

                if run_key in _last_run:
                    continue

                _last_run.add(run_key)

                threading.Thread(
                    target=_run_schedule,
                    args=(schedule,),
                    daemon=True
                ).start()

        except Exception:
            pass

        time.sleep(20)


def _run_schedule(schedule):

    file_path = schedule["file_path"]

    printer = schedule["printer"]

    copies = schedule["copies"]

    paper_size = schedule["paper_size"]

    orientation = schedule["orientation"]

    color_mode = schedule["color_mode"]

    duplex = bool(schedule["duplex"])

    try:

        if not os.path.exists(file_path):

            add_job(
                file_path,
                printer,
                copies,
                "schedule",
                "Failed",
                "Scheduled file does not exist",
                paper_size,
                orientation,
                color_mode,
                duplex
            )

            return

        result = submit_print(
            file_path,
            printer,
            copies,
            paper_size,
            orientation,
            color_mode,
            duplex
        )

        if result and result.get("ok"):

            add_job(
                file_path,
                printer,
                copies,
                "schedule",
                "Success",
                None,
                paper_size,
                orientation,
                color_mode,
                duplex
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
                copies,
                "schedule",
                "Failed",
                error,
                paper_size,
                orientation,
                color_mode,
                duplex
            )

    except Exception as e:

        add_job(
            file_path,
            printer,
            copies,
            "schedule",
            "Failed",
            str(e),
            paper_size,
            orientation,
            color_mode,
            duplex
        )


def start_scheduler():

    global _started

    if _started:
        return

    _started = True

    thread = threading.Thread(
        target=_schedule_loop,
        daemon=True,
        name="Scheduler"
    )

    thread.start()
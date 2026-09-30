import os

from flask import (
    Flask,
    jsonify,
    render_template,
    request
)

from werkzeug.utils import secure_filename

from services.database import (
    init_db,
    add_job,
    recent_jobs,
    add_schedule,
    list_schedules,
    toggle_schedule,
    delete_schedule
)

from services.printer_manager import (
    list_printers,
    get_default_printer,
    printer_status
)

from services.print_queue import (
    start_queue,
    submit_print,
    queue_status
)

from services.scheduler import (
    start_scheduler
)

from services.file_watcher import (
    start_watcher
)


# =========================================================
# APPLICATION
# =========================================================

app = Flask(__name__)

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

MANUAL_PRINT_DIR = os.path.join(
    DATA_DIR,
    "manual_prints"
)

SCHEDULED_FILES_DIR = os.path.join(
    DATA_DIR,
    "scheduled_files"
)

os.makedirs(
    MANUAL_PRINT_DIR,
    exist_ok=True
)

os.makedirs(
    SCHEDULED_FILES_DIR,
    exist_ok=True
)


# =========================================================
# SUPPORTED FILE TYPES
# =========================================================

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


# =========================================================
# INITIALIZE SERVICES
# =========================================================

init_db()

start_queue()

start_scheduler()

start_watcher()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_copies(value):
    """
    Validate number of copies.
    """

    try:
        copies = int(value)
    except (TypeError, ValueError):

        raise ValueError(
            "Copies must be a number."
        )

    if copies < 1 or copies > 99:

        raise ValueError(
            "Copies must be between 1 and 99."
        )

    return copies


def get_print_settings(source):
    """
    Read and validate print settings from
    either request.form or a dictionary.
    """

    if hasattr(source, "get"):

        paper_size = (
            source.get(
                "paper_size",
                "A4"
            )
            or "A4"
        ).strip()

        orientation = (
            source.get(
                "orientation",
                "Portrait"
            )
            or "Portrait"
        ).strip()

        color_mode = (
            source.get(
                "color_mode",
                "Color"
            )
            or "Color"
        ).strip()

        duplex_value = str(
            source.get(
                "duplex",
                "false"
            )
        ).strip().lower()

    else:

        paper_size = "A4"
        orientation = "Portrait"
        color_mode = "Color"
        duplex_value = "false"

    if paper_size not in [
        "A4"
    ]:

        raise ValueError(
            "Invalid paper size."
        )

    if orientation not in [
        "Portrait",
        "Landscape"
    ]:

        raise ValueError(
            "Invalid orientation."
        )

    if color_mode not in [
        "Color",
        "B&W"
    ]:

        raise ValueError(
            "Invalid color mode."
        )

    duplex = duplex_value in [
        "true",
        "1",
        "yes",
        "on"
    ]

    return (
        paper_size,
        orientation,
        color_mode,
        duplex
    )


def validate_uploaded_file(uploaded_file):

    if uploaded_file is None:

        raise ValueError(
            "Please select a file."
        )

    if not uploaded_file.filename:

        raise ValueError(
            "Please select a file."
        )

    filename = secure_filename(
        uploaded_file.filename
    )

    if not filename:

        raise ValueError(
            "Invalid file name."
        )

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in SUPPORTED_EXTENSIONS:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    return filename


def save_uploaded_file(
    uploaded_file,
    folder
):

    filename = validate_uploaded_file(
        uploaded_file
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    file_path = os.path.join(
        folder,
        filename
    )

    uploaded_file.save(
        file_path
    )

    return file_path


# =========================================================
# MAIN PAGE
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# =========================================================
# PRINTERS
# =========================================================

@app.route(
    "/api/printers",
    methods=["GET"]
)
def get_printers():

    try:

        printers = list_printers()

        default_printer = (
            get_default_printer()
        )

        return jsonify({
            "ok": True,
            "printers": printers,
            "default_printer": default_printer
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e),
            "printers": [],
            "default_printer": None
        }), 500


# =========================================================
# PRINTER STATUS
# =========================================================

@app.route(
    "/api/printer-status",
    methods=["GET"]
)
def get_printer_status():

    printer = request.args.get(
        "printer",
        ""
    ).strip()

    if not printer:

        printer = get_default_printer()

    if not printer:

        return jsonify({
            "ok": False,
            "error": "No printer selected."
        }), 400

    try:

        status = printer_status(
            printer
        )

        return jsonify({
            "ok": True,
            "printer": printer,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "printer": printer,
            "error": str(e)
        }), 500


# =========================================================
# SYSTEM STATUS
# =========================================================
# Kept for compatibility with the backend.
# The dashboard does not need to display this section.

@app.route(
    "/api/system-status",
    methods=["GET"]
)
def get_system_status():

    try:

        printer = get_default_printer()

        printer_info = None

        if printer:

            try:

                printer_info = printer_status(
                    printer
                )

            except Exception as e:

                printer_info = {
                    "error": str(e)
                }

        return jsonify({
            "ok": True,
            "printer": printer,
            "printer_status": printer_info,
            "queue": queue_status()
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# =========================================================
# MANUAL PRINT
# =========================================================

@app.route(
    "/api/print",
    methods=["POST"]
)
def manual_print():

    file_path = None

    try:

        # -------------------------------------------------
        # PRINTER
        # -------------------------------------------------

        printer = request.form.get(
            "printer",
            ""
        ).strip()

        if not printer:

            return jsonify({
                "ok": False,
                "error": "Please select a printer."
            }), 400

        # -------------------------------------------------
        # COPIES
        # -------------------------------------------------

        copies = get_copies(
            request.form.get(
                "copies",
                "1"
            )
        )

        # -------------------------------------------------
        # PRINT SETTINGS
        # -------------------------------------------------

        (
            paper_size,
            orientation,
            color_mode,
            duplex
        ) = get_print_settings(
            request.form
        )

        # -------------------------------------------------
        # FILE
        # -------------------------------------------------

        uploaded_file = request.files.get(
            "file"
        )

        file_path = save_uploaded_file(
            uploaded_file,
            MANUAL_PRINT_DIR
        )

        # -------------------------------------------------
        # SEND TO PRINT QUEUE
        # -------------------------------------------------

        result = submit_print(
            file_path,
            printer,
            copies,
            paper_size,
            orientation,
            color_mode,
            duplex
        )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if result and result.get("ok"):

            add_job(
                file_path=file_path,
                printer=printer,
                copies=copies,
                trigger_type="manual",
                status="Success",
                error=None,
                paper_size=paper_size,
                orientation=orientation,
                color_mode=color_mode,
                duplex=duplex
            )

            return jsonify({
                "ok": True,
                "message": "Print completed successfully.",
                "file": os.path.basename(
                    file_path
                ),
                "printer": printer,
                "status": "Success"
            }), 200

        # -------------------------------------------------
        # PRINT FAILED
        # -------------------------------------------------

        error_message = (
            result.get("error")
            if result
            else "Unknown printing error."
        )

        add_job(
            file_path=file_path,
            printer=printer,
            copies=copies,
            trigger_type="manual",
            status="Failed",
            error=error_message,
            paper_size=paper_size,
            orientation=orientation,
            color_mode=color_mode,
            duplex=duplex
        )

        return jsonify({
            "ok": False,
            "error": error_message,
            "status": "Failed"
        }), 500

    except ValueError as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400

    except Exception as e:

        error_message = str(e)

        # If a file was already saved but an unexpected
        # error occurred, record the failed job.

        if file_path:

            try:

                printer = request.form.get(
                    "printer",
                    ""
                ).strip()

                copies = int(
                    request.form.get(
                        "copies",
                        "1"
                    )
                )

                (
                    paper_size,
                    orientation,
                    color_mode,
                    duplex
                ) = get_print_settings(
                    request.form
                )

                add_job(
                    file_path=file_path,
                    printer=printer,
                    copies=copies,
                    trigger_type="manual",
                    status="Failed",
                    error=error_message,
                    paper_size=paper_size,
                    orientation=orientation,
                    color_mode=color_mode,
                    duplex=duplex
                )

            except Exception:
                pass

        return jsonify({
            "ok": False,
            "error": error_message,
            "status": "Failed"
        }), 500


# =========================================================
# RECENT PRINT JOBS
# =========================================================

@app.route(
    "/api/jobs",
    methods=["GET"]
)
def get_jobs():

    try:

        jobs = recent_jobs(
            limit=50
        )

        # Make the API cleaner for the dashboard.
        # Keep the full path internally, but send only
        # the file name as the displayed document name.

        cleaned_jobs = []

        for job in jobs:

            item = dict(job)

            item["file_name"] = os.path.basename(
                item.get(
                    "file_path",
                    ""
                )
            )

            item["duplex"] = bool(
                item.get(
                    "duplex",
                    0
                )
            )

            cleaned_jobs.append(
                item
            )

        return jsonify({
            "ok": True,
            "jobs": cleaned_jobs
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e),
            "jobs": []
        }), 500


# =========================================================
# GET SCHEDULES
# =========================================================

@app.route(
    "/api/schedules",
    methods=["GET"]
)
def get_schedules():

    try:

        schedules = list_schedules()

        cleaned_schedules = []

        for schedule in schedules:

            item = dict(schedule)

            item["file_name"] = os.path.basename(
                item.get(
                    "file_path",
                    ""
                )
            )

            item["enabled"] = bool(
                item.get(
                    "enabled",
                    1
                )
            )

            item["duplex"] = bool(
                item.get(
                    "duplex",
                    0
                )
            )

            cleaned_schedules.append(
                item
            )

        return jsonify({
            "ok": True,
            "schedules": cleaned_schedules
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e),
            "schedules": []
        }), 500


# =========================================================
# CREATE SCHEDULE
# =========================================================

@app.route(
    "/api/schedules",
    methods=["POST"]
)
def create_schedule():

    uploaded_file = None
    file_path = None

    try:

        # -------------------------------------------------
        # ACCEPT FORM DATA
        # -------------------------------------------------

        if request.form:

            source = request.form

            printer = source.get(
                "printer",
                ""
            ).strip()

            print_time = source.get(
                "print_time",
                source.get(
                    "time",
                    ""
                )
            ).strip()

            days = source.get(
                "days",
                "Every day"
            ).strip()

            copies = get_copies(
                source.get(
                    "copies",
                    "1"
                )
            )

            (
                paper_size,
                orientation,
                color_mode,
                duplex
            ) = get_print_settings(
                source
            )

            uploaded_file = request.files.get(
                "file"
            )

        # -------------------------------------------------
        # ACCEPT JSON
        # -------------------------------------------------

        else:

            data = request.get_json(
                silent=True
            ) or {}

            printer = str(
                data.get(
                    "printer",
                    ""
                )
            ).strip()

            print_time = str(
                data.get(
                    "print_time",
                    data.get(
                        "time",
                        ""
                    )
                )
            ).strip()

            days = str(
                data.get(
                    "days",
                    "Every day"
                )
            ).strip()

            copies = get_copies(
                data.get(
                    "copies",
                    1
                )
            )

            (
                paper_size,
                orientation,
                color_mode,
                duplex
            ) = get_print_settings(
                data
            )

        # -------------------------------------------------
        # VALIDATE PRINTER
        # -------------------------------------------------

        if not printer:

            return jsonify({
                "ok": False,
                "error": "Please select a printer."
            }), 400

        # -------------------------------------------------
        # VALIDATE TIME
        # -------------------------------------------------

        if not print_time:

            return jsonify({
                "ok": False,
                "error": "Please select a schedule time."
            }), 400

        # -------------------------------------------------
        # VALIDATE TIME FORMAT
        # -------------------------------------------------

        try:

            hour, minute = map(
                int,
                print_time.split(":")
            )

            if not (
                0 <= hour <= 23
                and
                0 <= minute <= 59
            ):

                raise ValueError

            print_time = (
                f"{hour:02d}:{minute:02d}"
            )

        except Exception:

            return jsonify({
                "ok": False,
                "error": "Invalid time. Use HH:MM format."
            }), 400

        # -------------------------------------------------
        # FILE
        # -------------------------------------------------

        if uploaded_file is not None:

            file_path = save_uploaded_file(
                uploaded_file,
                SCHEDULED_FILES_DIR
            )

        else:

            # JSON schedule can provide an existing file path.

            data = request.get_json(
                silent=True
            ) or {}

            supplied_path = data.get(
                "file_path"
            )

            if not supplied_path:

                return jsonify({
                    "ok": False,
                    "error": "Please select a file."
                }), 400

            file_path = os.path.abspath(
                supplied_path
            )

            if not os.path.isfile(
                file_path
            ):

                return jsonify({
                    "ok": False,
                    "error": "Selected file does not exist."
                }), 400

        # -------------------------------------------------
        # CREATE SCHEDULE
        # -------------------------------------------------

        schedule_id = add_schedule(
            file_path=file_path,
            printer=printer,
            print_time=print_time,
            days=days,
            copies=copies,
            paper_size=paper_size,
            orientation=orientation,
            color_mode=color_mode,
            duplex=duplex
        )

        return jsonify({
            "ok": True,
            "message": "Schedule created successfully.",
            "schedule_id": schedule_id
        }), 200

    except ValueError as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# =========================================================
# ENABLE / DISABLE SCHEDULE
# =========================================================

@app.route(
    "/api/schedules/<int:schedule_id>/toggle",
    methods=["POST"]
)
def toggle_schedule_route(
    schedule_id
):

    try:

        toggle_schedule(
            schedule_id
        )

        return jsonify({
            "ok": True,
            "message": "Schedule status updated."
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# =========================================================
# DELETE SCHEDULE
# =========================================================

@app.route(
    "/api/schedules/<int:schedule_id>",
    methods=["DELETE"]
)
def delete_schedule_route(
    schedule_id
):

    try:

        delete_schedule(
            schedule_id
        )

        return jsonify({
            "ok": True,
            "message": "Schedule deleted."
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# =========================================================
# QUEUE STATUS
# =========================================================

@app.route(
    "/api/queue-status",
    methods=["GET"]
)
def get_queue_status():

    try:

        return jsonify({
            "ok": True,
            **queue_status()
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# =========================================================
# APPLICATION START
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
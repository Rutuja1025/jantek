import os
import platform
import subprocess

import win32print
import win32ui
import pymupdf

from PIL import Image, ImageWin


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


def list_printers():
    printers = []

    flags = (
        win32print.PRINTER_ENUM_LOCAL
        | win32print.PRINTER_ENUM_CONNECTIONS
    )

    try:
        printer_data = win32print.EnumPrinters(
            flags,
            None,
            2
        )

        for item in printer_data:
            name = item.get("pPrinterName")

            if name and name not in printers:
                printers.append(name)

    except Exception:
        pass

    return printers


def get_default_printer():
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return None


def printer_status(printer):
    if not printer:
        return {
            "available": False,
            "message": "No printer selected"
        }

    try:
        printers = list_printers()

        if printer not in printers:
            return {
                "available": False,
                "message": "Printer not found"
            }

        handle = win32print.OpenPrinter(printer)

        try:
            info = win32print.GetPrinter(handle, 2)

            status = info.get("Status", 0)

            return {
                "available": True,
                "printer": printer,
                "status": status,
                "message": "Printer available"
            }

        finally:
            win32print.ClosePrinter(handle)

    except Exception as e:
        return {
            "available": False,
            "printer": printer,
            "message": str(e)
        }


def _get_render_size(printable_width, printable_height, orientation):
    """
    Determines the render area.

    Windows printer drivers report the actual printable area.
    """

    if orientation == "Landscape":
        return printable_height, printable_width

    return printable_width, printable_height


def _print_pdf(
    pdf_path,
    printer,
    copies=1,
    paper_size="A4",
    orientation="Portrait",
    color_mode="Color",
    duplex=False
):
    document = None
    dc = None

    try:
        document = pymupdf.open(pdf_path)

        if document.page_count == 0:
            return {
                "ok": False,
                "error": "PDF contains no pages"
            }

        dc = win32ui.CreateDC()

        # IMPORTANT:
        # PyCDC uses CreatePrinterDC().
        # Do not use dc.CreateDC().
        dc.CreatePrinterDC(printer)

        printable_width = dc.GetDeviceCaps(8)
        printable_height = dc.GetDeviceCaps(10)

        render_width, render_height = _get_render_size(
            printable_width,
            printable_height,
            orientation
        )

        # Small margin around the printable area
        margin = 20

        render_width = max(
            100,
            render_width - (margin * 2)
        )

        render_height = max(
            100,
            render_height - (margin * 2)
        )

        for copy_number in range(copies):

            dc.StartDoc(
                os.path.basename(pdf_path)
            )

            try:

                for page_number in range(document.page_count):

                    page = document.load_page(page_number)

                    page_rect = page.rect

                    # -------------------------------------------------
                    # Landscape
                    # -------------------------------------------------
                    if orientation == "Landscape":
                        if page_rect.height > page_rect.width:
                            page = document.load_page(page_number)

                            matrix = pymupdf.Matrix(
                                1,
                                1
                            ).prerotate(90)

                            pix = page.get_pixmap(
                                matrix=matrix,
                                alpha=False
                            )
                        else:
                            scale_x = render_width / page_rect.width
                            scale_y = render_height / page_rect.height

                            scale = min(
                                scale_x,
                                scale_y
                            )

                            matrix = pymupdf.Matrix(
                                scale,
                                scale
                            )

                            pix = page.get_pixmap(
                                matrix=matrix,
                                alpha=False
                            )

                    # -------------------------------------------------
                    # Portrait
                    # -------------------------------------------------
                    else:
                        scale_x = render_width / page_rect.width
                        scale_y = render_height / page_rect.height

                        scale = min(
                            scale_x,
                            scale_y
                        )

                        matrix = pymupdf.Matrix(
                            scale,
                            scale
                        )

                        pix = page.get_pixmap(
                            matrix=matrix,
                            alpha=False
                        )

                    image = Image.frombytes(
                        "RGB",
                        [pix.width, pix.height],
                        pix.samples
                    )

                    # -------------------------------------------------
                    # B&W
                    # -------------------------------------------------
                    if color_mode == "B&W":
                        image = image.convert("L")
                        image = image.convert("RGB")

                    # -------------------------------------------------
                    # Make sure the image fits the printer area
                    # -------------------------------------------------
                    image.thumbnail(
                        (
                            render_width,
                            render_height
                        ),
                        Image.Resampling.LANCZOS
                    )

                    x = (
                        printable_width - image.width
                    ) // 2

                    y = (
                        printable_height - image.height
                    ) // 2

                    dib = ImageWin.Dib(image)

                    dc.StartPage()

                    try:
                        dib.draw(
                            dc.GetHandleOutput(),
                            (
                                x,
                                y,
                                x + image.width,
                                y + image.height
                            )
                        )

                    finally:
                        dc.EndPage()

            finally:
                dc.EndDoc()

        return {
            "ok": True,
            "message": "Printing completed successfully"
        }

    except Exception as e:

        return {
            "ok": False,
            "error": f"PDF printing failed: {e}"
        }

    finally:

        if dc is not None:
            try:
                dc.DeleteDC()
            except Exception:
                # Some Windows printer drivers throw
                # "DeleteDC failed" even after a successful print.
                pass

        if document is not None:
            try:
                document.close()
            except Exception:
                pass


def _print_office_file(
    file_path,
    printer
):
    """
    Uses the Windows PrintTo shell command for Office/text files.
    """

    try:
        extension = os.path.splitext(file_path)[1].lower()

        if extension not in SUPPORTED_EXTENSIONS:
            return {
                "ok": False,
                "error": f"Unsupported file type: {extension}"
            }

        if extension == ".txt":
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f'Start-Process -FilePath "{file_path}" '
                    f'-Verb PrintTo -ArgumentList \'"{printer}"\''
                ],
                check=True
            )

            return {
                "ok": True,
                "message": "Printing started"
            }

        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f'Start-Process -FilePath "{file_path}" '
                f'-Verb PrintTo -ArgumentList \'"{printer}"\''
            ],
            check=True
        )

        return {
            "ok": True,
            "message": "Printing started"
        }

    except Exception as e:

        return {
            "ok": False,
            "error": f"Office printing failed: {e}"
        }


def print_file(
    file_path,
    printer,
    copies=1,
    paper_size="A4",
    orientation="Portrait",
    color_mode="Color",
    duplex=False
):

    if platform.system() != "Windows":
        return {
            "ok": False,
            "error": "This printing system currently supports Windows only"
        }

    if not file_path:
        return {
            "ok": False,
            "error": "No file specified"
        }

    if not os.path.exists(file_path):
        return {
            "ok": False,
            "error": "File does not exist"
        }

    if not printer:
        return {
            "ok": False,
            "error": "No printer selected"
        }

    if printer not in list_printers():
        return {
            "ok": False,
            "error": "Selected printer is not available"
        }

    try:
        copies = int(copies)
    except Exception:
        return {
            "ok": False,
            "error": "Copies must be a number"
        }

    if copies < 1 or copies > 99:
        return {
            "ok": False,
            "error": "Copies must be between 1 and 99"
        }

    extension = os.path.splitext(file_path)[1].lower()

    if extension not in SUPPORTED_EXTENSIONS:
        return {
            "ok": False,
            "error": f"Unsupported file type: {extension}"
        }

    if paper_size not in {"A4"}:
        return {
            "ok": False,
            "error": "Only A4 is currently supported"
        }

    if orientation not in {"Portrait", "Landscape"}:
        return {
            "ok": False,
            "error": "Invalid orientation"
        }

    if color_mode not in {"Color", "B&W"}:
        return {
            "ok": False,
            "error": "Invalid color mode"
        }

    if extension == ".pdf":

        return _print_pdf(
            file_path,
            printer,
            copies,
            paper_size,
            orientation,
            color_mode,
            duplex
        )

    return _print_office_file(
        file_path,
        printer
    )
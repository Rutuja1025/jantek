# Automatic Printing System

Initial real-system foundation for Windows.

## Included
- One-click Print Now
- Multiple scheduled print times
- File-folder automatic printing foundation
- Windows installed-printer discovery
- SQLite print history and schedules
- Printer status endpoint
- Basic queue-ready architecture

## Run
1. Create and activate a virtual environment.
2. `pip install -r requirements.txt`
3. `python app.py`
4. Open `http://127.0.0.1:5000`

## Important
Physical printing is designed for Windows and uses the installed Windows printer/driver. Test first with a non-sensitive PDF on the home HP printer.

The database is created automatically at `data/printing.db` on first run.

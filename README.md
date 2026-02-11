# Construction Intelligence - Deployment

This project is a Python-based application for tracking and analyzing planning applications. It includes a web scraper, database management, and a Flask web interface.

## Prerequisites

- Python 3.8+
- Git

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd "Construction Intelligence - Deployment"
   ```

2. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Setup

Before running the application for the first time, initialize the database:

```bash
python database.py
```

Then, run the sync manager to populate the initial data:

```bash
python sync_manager.py
```

## Running the Application

Start the Flask development server:

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`.

## Project Structure

- `app.py`: Main Flask application.
- `database.py`: Database initialization and connection logic.
- `scraper.py`: Web scraping functionality.
- `sync_manager.py`: Handles data synchronization and updates.
- `live_search.py`: Modules for searching recent decisions.
- `templates/`: HTML templates for the web interface.

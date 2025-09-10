# Shift Handover Web Application

This is a Flask-based web application for managing shift handovers, incidents, and engineer rosters. It uses MySQL for data storage, Bootstrap for UI, Chart.js/Plotly for dashboard charts, and supports email notifications and export features.

## Features
- Authentication (static credentials: admin/admin)
- Shift handover form with incident and key point entries
- Dashboard with charts and overview
- Shift roster calendar view
- Email notifications on handover submission
- Export incidents/key points to PDF/CSV

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure `.env` for MySQL and SMTP settings.
3. Initialize the database (run a Python shell):
   ```python
   from app import db
   db.create_all()
   ```
4. Run the app:
   ```bash
   python app.py
   ```

## Docker Setup

### Quick Start

1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
2. The Flask app will be available at [http://localhost:5000](http://localhost:5000)

3. Initialize the database (in a new terminal):
   ```bash
   docker-compose exec web flask shell
   >>> from app import db
   >>> db.create_all()
   >>> exit()
   ```

### Notes
- The MySQL database is accessible at `db:3306` from the Flask container.
- Environment variables are set in `.env` and overridden in `docker-compose.yml` as needed.
- For production, update credentials and consider using a production-ready WSGI server (e.g., gunicorn).

## Notes
- For proof-of-concept, authentication uses static credentials.
- Replace SMTP and DB credentials in `.env` for production use.

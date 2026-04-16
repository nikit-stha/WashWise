# WashWise

WashWise is a Flask-based hostel laundry management system for students and laundry staff. Students can build a digital wardrobe, create laundry deposits, track their status, and receive dashboard notifications. Staff can manage deposit availability, collection availability, and update laundry progress.

## Features

- Student and staff registration/login flows
- Email OTP verification for new accounts
- Password reset emails for students and staff
- Student wardrobe with image uploads and browser-side image optimization
- Laundry deposit creation from wardrobe items
- Active-deposit restriction: one open deposit per student until collection
- Deposit status tracking: `Not Given`, `Processing`, `Completed`, `Collected`
- Staff dashboard controls for opening/closing deposits and collections
- User dashboard notification bell for deposit/collection availability and completed laundry
- Staff deposit search and status filtering
- QR code generation and scan endpoints for completed deposits
- Light/dark theme support

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF / WTForms
- Flask-Mail
- SQLite by default, configurable via `DATABASE_URL`
- Pillow for image processing

## Project Structure

```text
WashWise/
├── app/
│   ├── config/          # App configuration
│   ├── forms/           # WTForms form classes
│   ├── models/          # SQLAlchemy models
│   ├── routes/          # Flask route handlers
│   ├── services/        # Business logic
│   ├── static/          # CSS, icons, uploads
│   ├── templates/       # Jinja templates
│   └── utils/           # Shared helpers
├── requirements.txt
├── run.py               # Local development entry point
└── wsgi.py              # WSGI entry point for hosting
```

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd WashWise
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a `.env` file

Create `.env` in the project root:

```env
SECRET_KEY=change-this-to-a-long-random-secret
STAFF_REGISTRATION_KEY=change-this-staff-key

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-app-password
MAIL_DEFAULT_SENDER=WashWise <your-email@example.com>

ADMINS=your-email@example.com
PASSWORD_RESET_TOKEN_EXPIRES=600
EMAIL_VERIFICATION_OTP_EXPIRES=600
```

Do not commit real `.env` values to GitHub. For Gmail, use an app password instead of your normal account password.

### 5. Run the app

```bash
python run.py
```

The app will create the SQLite database automatically at `app/app.db` if it does not exist.

## Default URLs

- Home: `http://127.0.0.1:5000/`
- Student login: `http://127.0.0.1:5000/user/login`
- Student registration: `http://127.0.0.1:5000/user/register`
- Staff login: `http://127.0.0.1:5000/staff/login`
- Staff registration: `http://127.0.0.1:5000/staff/register`

## Email Notes

WashWise sends verification OTPs and password reset links through SMTP. If email sending fails with a network error such as `Network is unreachable`, check that:

- The server has outbound network access.
- SMTP traffic is allowed by your host.
- The mail username, password, sender, and server settings are correct.
- Gmail accounts use an app password.

If email is not configured, registration can start but users may not receive OTPs.

## Database

By default, the app uses SQLite:

```text
app/app.db
```

To use another database, set `DATABASE_URL` in your environment:

```env
DATABASE_URL=postgresql://user:password@host:5432/database_name
```

The app also supports old Heroku-style `postgres://` URLs by converting them to `postgresql://`.

## Uploads

Uploaded wardrobe and deposit images are stored under:

```text
app/static/uploads/
```

Images are converted/compressed to WebP on upload. The project ignores upload files in Git so user images do not get committed.

## Deployment

Use `wsgi.py` for WSGI hosting:

```python
from app import app as application
```

For production:

- Set a strong `SECRET_KEY`.
- Set `FLASK_ENV=production`.
- Configure a production database through `DATABASE_URL`.
- Configure SMTP credentials through environment variables.
- Keep `.env`, `app/app.db`, and `app/static/uploads/` out of version control.

## Development Checks

Run a Python syntax check:

```bash
python -m compileall app
```

No dedicated automated test suite is currently included.

## License

Add a license before publishing if this project will be shared publicly.

- By WashWise Team

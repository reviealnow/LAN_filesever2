# Project Structure Guide

This guide defines a reusable structure for contributors who want to run, maintain, or extend this project.

## Current Tree

```text
LAN_filesever2/
├── app.py                  # Flask app factory, routes, and runtime startup config
├── auth.py                 # Register/login/logout + login_required decorator
├── config.py               # App constants and upload/security settings
├── db.py                   # SQLite connection, schema init, query helpers
├── file_service.py         # File validation, save/list/get/delete logic
├── requirements.txt        # Python dependencies
├── README.md               # Setup and usage documentation
├── PROJECT_STRUCTURE.md    # This file
├── LAN_fileserver.md       # Original system design document
├── LICENSE
├── docs/
│   └── GETTING_STARTED.md  # Contributor onboarding notes
├── scripts/
│   └── start.sh            # One-command bootstrap + launch script
├── static/
│   └── styles.css          # UI styling + toast notifications
├── templates/
│   ├── base.html           # Shared layout + flash toast rendering
│   ├── landing.html        # Landing page
│   ├── register.html       # Sign-up page
│   ├── login.html          # Sign-in page
│   └── files.html          # Upload/list/download/delete page
├── tests/
│   └── README.md           # Test placement guidance
├── instance/
│   └── lan_fileserver.db   # SQLite DB (auto-created)
├── logs/
│   └── .gitkeep            # Placeholder for local logs
└── uploads/
    └── .gitkeep            # Upload directory placeholder
```

## Responsibility Boundaries

- `app.py`
  - Keep HTTP routing and request/response handling here
  - Do not move heavy business logic into routes
- `auth.py`
  - Keep all account/session validation logic here
- `file_service.py`
  - Keep upload and file permission logic here
- `db.py`
  - Keep SQL schema and low-level DB helpers here
- `templates/` and `static/`
  - Keep rendering and UI-only behavior here

## Extension Rules

- New feature with persistent data: add schema updates in `db.py`
- New protected page: use `login_required`
- New file-related rules: implement in `file_service.py`
- New UI pages: add template + route in `app.py`
- Keep environment-driven settings in `config.py`

## Reuse Checklist For New Teams

1. Clone repository.
2. Create virtual environment and install dependencies.
3. Verify HTTPS mode and cert strategy for your LAN.
4. Confirm allowed file extensions match your policy.
5. Add tests under `tests/` before major changes.
6. Document any new environment variables in `README.md`.

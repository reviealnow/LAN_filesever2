"""Throwaway preview runner: seeds a temp DB + uploads dir, runs the real app
over plain HTTP so the Proposal-B dashboard can be screenshotted. Not committed."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config

# Redirect storage to a temp sandbox BEFORE the app/db touch anything.
_tmp = Path(tempfile.mkdtemp(prefix="lanfs_preview_"))
Config.DATABASE = _tmp / "preview.db"
Config.UPLOAD_FOLDER = _tmp / "uploads"
Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

from werkzeug.security import generate_password_hash  # noqa: E402

import app as app_module  # noqa: E402
from db import execute, init_db  # noqa: E402

flask_app = app_module.create_app()


def seed():
    with flask_app.app_context():
        init_db()
        users = [
            ("nelson", "nelson@office.local"),
            ("amy", "amy@office.local"),
            ("chen", "chen@office.local"),
        ]
        ids = {}
        for name, email in users:
            ids[name] = execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash("password123")),
            )

        files = [
            ("Q2-report.pdf", 2_516_582, "amy"),
            ("capture.pcapng", 48_211_004, "nelson"),
            ("floorplan.png", 901_120, "chen"),
            ("inventory.csv", 319_488, "amy"),
            ("debug.log", 55_296, "nelson"),
        ]
        for fname, size, owner in files:
            p = Config.UPLOAD_FOLDER / fname
            p.write_bytes(b"0")  # placeholder; download not exercised in preview
            execute(
                "INSERT INTO files (filename, filepath, size, uploaded_by) VALUES (?, ?, ?, ?)",
                (fname, str(p), size, ids[owner]),
            )

        post1 = execute(
            "INSERT INTO bulletin_posts (title, body, created_by) VALUES (?, ?, ?)",
            ("Server maintenance Fri 6pm", "Uploads paused ~30 min while we expand storage.", ids["nelson"]),
        )
        execute(
            "INSERT INTO bulletin_posts (title, body, created_by) VALUES (?, ?, ?)",
            ("Please tag firmware builds", "Use vX.Y in the filename so we can sort releases.", ids["amy"]),
        )
        c1 = execute(
            "INSERT INTO bulletin_comments (post_id, parent_comment_id, body, created_by) VALUES (?, ?, ?, ?)",
            (post1, None, "Thanks for the heads up!", ids["amy"]),
        )
        execute(
            "INSERT INTO bulletin_comments (post_id, parent_comment_id, body, created_by) VALUES (?, ?, ?, ?)",
            (post1, c1, "Will the share stay mounted?", ids["chen"]),
        )


if __name__ == "__main__":
    seed()
    print(f"Preview DB: {Config.DATABASE}")
    flask_app.run(host="127.0.0.1", port=8898, debug=False, ssl_context=None)

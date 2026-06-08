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
    import random
    from datetime import datetime, timedelta

    rng = random.Random(42)  # deterministic so screenshots are stable

    with flask_app.app_context():
        init_db()
        users = [
            ("nelson", "nelson@office.local"),
            ("amy", "amy@office.local"),
            ("chen", "chen@office.local"),
            ("wei", "wei@office.local"),
            ("lin", "lin@office.local"),
        ]
        ids = {}
        for name, email in users:
            ids[name] = execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash("password123")),
            )

        # Back-dated uploads across the last 14 days so the time-series chart
        # has shape. Extensions/owners weighted to make the donut + top-uploaders
        # charts meaningful.
        ext_sizes = {
            "pdf": (800_000, 4_000_000),
            "pcapng": (10_000_000, 50_000_000),
            "png": (200_000, 2_000_000),
            "csv": (20_000, 600_000),
            "log": (5_000, 120_000),
            "json": (2_000, 80_000),
            "txt": (1_000, 40_000),
        }
        ext_pool = ["pdf", "pdf", "pcapng", "png", "png", "csv", "log", "json", "txt"]
        owner_pool = ["nelson", "nelson", "nelson", "amy", "amy", "chen", "chen", "wei", "lin"]

        today = datetime.now()
        seq = 0
        for day_offset in range(13, -1, -1):
            day = today - timedelta(days=day_offset)
            # gentle upward trend: more uploads on recent days
            count = rng.randint(0, 2) + (13 - day_offset) // 3
            for _ in range(count):
                seq += 1
                ext = rng.choice(ext_pool)
                owner = rng.choice(owner_pool)
                lo, hi = ext_sizes[ext]
                size = rng.randint(lo, hi)
                fname = f"file_{seq:03d}.{ext}"
                ts = day.replace(
                    hour=rng.randint(8, 18), minute=rng.randint(0, 59), second=rng.randint(0, 59)
                )
                p = Config.UPLOAD_FOLDER / fname
                p.write_bytes(b"0")  # placeholder; download not exercised in preview
                execute(
                    "INSERT INTO files (filename, filepath, size, uploaded_by, uploaded_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (fname, str(p), size, ids[owner], ts.strftime("%Y-%m-%d %H:%M:%S")),
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

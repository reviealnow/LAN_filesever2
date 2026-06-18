from datetime import date, timedelta
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from db import execute, query_all, query_one


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def _unique_filename(original_name: str) -> str:
    safe_name = secure_filename(original_name)
    if not safe_name:
        raise ValueError("Invalid filename.")

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    candidate = upload_dir / safe_name
    stem = candidate.stem
    suffix = candidate.suffix
    idx = 1

    while candidate.exists():
        candidate = upload_dir / f"{stem}_{idx}{suffix}"
        idx += 1

    return candidate.name


def save_uploaded_file(file_storage, user_id: int) -> int:
    if file_storage.filename == "":
        raise ValueError("No file selected.")
    if not allowed_file(file_storage.filename):
        allowed = ", ".join(f".{ext}" for ext in sorted(current_app.config["ALLOWED_EXTENSIONS"]))
        raise ValueError(f"File type is not allowed. Accepted formats: {allowed}.")

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = _unique_filename(file_storage.filename)
    save_path = upload_dir / stored_name
    file_storage.save(save_path)
    size = save_path.stat().st_size

    return execute(
        "INSERT INTO files (filename, filepath, size, uploaded_by) VALUES (?, ?, ?, ?)",
        (stored_name, str(save_path), size, user_id),
    )


def list_files():
    return query_all(
        """
        SELECT f.id, f.filename, f.size, f.uploaded_at, f.uploaded_by, u.username
        FROM files AS f
        JOIN users AS u ON f.uploaded_by = u.id
        ORDER BY f.uploaded_at DESC, f.id DESC
        """
    )


def get_file_by_id(file_id: int):
    return query_one(
        """
        SELECT f.id, f.filename, f.filepath, f.size, f.uploaded_at, f.uploaded_by, u.username
        FROM files AS f
        JOIN users AS u ON f.uploaded_by = u.id
        WHERE f.id = ?
        """,
        (file_id,),
    )


# ---------------------------------------------------------------------------
# Dashboard aggregates (Phase 2 charts). Return plain JSON-serializable dicts
# so the data can drive either server-rendered SVG or a future Chart.js view.
# ---------------------------------------------------------------------------

def uploads_per_day(days: int = 14):
    """Files uploaded per calendar day for the last `days` days, zero-filled."""
    rows = query_all("SELECT date(uploaded_at) AS d, COUNT(*) AS c FROM files GROUP BY d")
    counts = {r["d"]: r["c"] for r in rows}
    today = date.today()
    series = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        series.append({
            "date": day.isoformat(),
            "label": f"{day.month}/{day.day}",
            "count": counts.get(day.isoformat(), 0),
        })
    return series


def files_by_type():
    """Aggregate file count and total size per extension, largest first."""
    rows = query_all("SELECT filename, size FROM files")
    agg: dict[str, dict] = {}
    for row in rows:
        name = row["filename"]
        ext = name.rsplit(".", 1)[1].lower() if "." in name else "other"
        entry = agg.setdefault(ext, {"ext": ext, "count": 0, "size": 0})
        entry["count"] += 1
        entry["size"] += row["size"]
    return sorted(agg.values(), key=lambda e: e["size"], reverse=True)


def top_uploaders(limit: int = 5):
    """Users ranked by number of files uploaded."""
    rows = query_all(
        """
        SELECT u.username AS username, COUNT(*) AS count
        FROM files AS f
        JOIN users AS u ON f.uploaded_by = u.id
        GROUP BY f.uploaded_by
        ORDER BY count DESC, u.username ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in rows]


def delete_file(file_row, requester_id: int) -> None:
    if file_row["uploaded_by"] != requester_id:
        raise PermissionError("You can only delete your own files.")

    path = Path(file_row["filepath"])
    if path.exists():
        path.unlink()

    execute("DELETE FROM files WHERE id = ?", (file_row["id"],))

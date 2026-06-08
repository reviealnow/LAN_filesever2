import os
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from auth import auth_bp, login_required
from bulletin_service import create_comment, create_post, list_posts
from config import Config
from db import close_db, init_db, query_one
from file_service import delete_file, get_file_by_id, list_files, save_uploaded_file


def _humanize_bytes(num_bytes: int) -> str:
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _build_activity(files, bulletin_posts, limit: int = 6):
    """Merge recent file uploads and bulletin posts/replies into one feed."""
    items = []
    for f in files:
        items.append({"actor": f["username"], "action": "uploaded", "target": f["filename"], "ts": f["uploaded_at"]})
    for post in bulletin_posts:
        items.append({"actor": post["username"], "action": "posted", "target": post["title"], "ts": post["created_at"]})
        for comment in post["comments"]:
            items.append({"actor": comment["username"], "action": "replied on", "target": post["title"], "ts": comment["created_at"]})
            for reply in comment["replies"]:
                items.append({"actor": reply["username"], "action": "replied on", "target": post["title"], "ts": reply["created_at"]})
    items.sort(key=lambda item: item["ts"] or "", reverse=True)
    return items[:limit]


def _count_replies(bulletin_posts) -> int:
    total = 0
    for post in bulletin_posts:
        for comment in post["comments"]:
            total += 1 + len(comment["replies"])
    return total


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    app.register_blueprint(auth_bp)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(_error):
        flash("File exceeds 50 MB limit.", "error")
        return redirect(url_for("files_page"))

    @app.route("/")
    def landing():
        if "user_id" in session:
            return redirect(url_for("files_page"))
        return render_template("landing.html")

    @app.route("/files")
    @login_required
    def files_page():
        files = list_files()
        bulletin_posts = list_posts()
        allowed_exts = sorted(app.config["ALLOWED_EXTENSIONS"])
        allowed_exts_label = ", ".join(f".{ext}" for ext in allowed_exts)
        accept_attr = ",".join(f".{ext}" for ext in allowed_exts)

        member_row = query_one("SELECT COUNT(*) AS count FROM users")
        stats = {
            "total_files": len(files),
            "storage_used": _humanize_bytes(sum(f["size"] for f in files)),
            "active_threads": len(bulletin_posts),
            "total_replies": _count_replies(bulletin_posts),
            "members": member_row["count"] if member_row else 0,
        }

        return render_template(
            "files.html",
            files=files,
            bulletin_posts=bulletin_posts,
            allowed_exts_label=allowed_exts_label,
            accept_attr=accept_attr,
            stats=stats,
            activity=_build_activity(files, bulletin_posts),
        )

    @app.route("/upload", methods=["POST"])
    @login_required
    def upload_file():
        uploaded = request.files.get("file")
        if uploaded is None:
            flash("No file provided.", "error")
            return redirect(url_for("files_page"))

        try:
            save_uploaded_file(uploaded, session["user_id"])
            flash("File uploaded successfully.", "success")
        except ValueError as exc:
            flash(str(exc), "error")

        return redirect(url_for("files_page"))

    @app.route("/download/<int:file_id>")
    @login_required
    def download_file(file_id: int):
        file_row = get_file_by_id(file_id)
        if file_row is None:
            abort(404)

        directory = Path(file_row["filepath"]).parent
        return send_from_directory(directory, file_row["filename"], as_attachment=True)

    @app.route("/delete/<int:file_id>", methods=["POST"])
    @login_required
    def remove_file(file_id: int):
        file_row = get_file_by_id(file_id)
        if file_row is None:
            abort(404)

        try:
            delete_file(file_row, session["user_id"])
            flash("File deleted.", "success")
        except PermissionError as exc:
            flash(str(exc), "error")

        return redirect(url_for("files_page"))

    @app.route("/bulletin/posts", methods=["POST"])
    @login_required
    def create_bulletin_post():
        title = request.form.get("title", "")
        body = request.form.get("body", "")

        try:
            create_post(title, body, session["user_id"])
            flash("Post published.", "success")
        except ValueError as exc:
            flash(str(exc), "error")

        return redirect(url_for("files_page"))

    @app.route("/bulletin/posts/<int:post_id>/comments", methods=["POST"])
    @login_required
    def create_bulletin_comment(post_id: int):
        body = request.form.get("body", "")
        parent_comment_id = request.form.get("parent_comment_id", "").strip()
        try:
            reply_to = int(parent_comment_id) if parent_comment_id else None
        except ValueError:
            flash("Reply target is invalid.", "error")
            return redirect(url_for("files_page"))

        try:
            create_comment(post_id, body, session["user_id"], reply_to)
            flash("Reply added.", "success")
        except ValueError as exc:
            flash(str(exc), "error")

        return redirect(url_for("files_page"))

    return app


app = create_app()


def resolve_ssl_context():
    enable_https = os.getenv("ENABLE_HTTPS", "1").lower() not in {"0", "false", "no"}
    if not enable_https:
        return None

    cert_file = os.getenv("SSL_CERT_FILE")
    key_file = os.getenv("SSL_KEY_FILE")
    if cert_file and key_file:
        return cert_file, key_file

    # Development fallback: generate a temporary self-signed certificate.
    return "adhoc"


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8443"))
    debug = os.getenv("FLASK_DEBUG", "1").lower() not in {"0", "false", "no"}
    app.run(host=host, port=port, debug=debug, ssl_context=resolve_ssl_context())

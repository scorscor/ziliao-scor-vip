from __future__ import annotations

import hashlib
import os
import re
import uuid
import zipfile
from datetime import date, datetime
from functools import wraps
from pathlib import PurePosixPath

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import or_
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .extensions import db
from .models import AdminUser, Resource, SiteConfig, china_today


bp = Blueprint("admin", __name__, url_prefix="/admin")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
COVER_HINTS = ("cover", "poster", "preview", "thumb", "thumbnail", "banner", "logo")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "resource"


def unique_slug(value: str, resource_id: int | None = None) -> str:
    base = slugify(value)
    candidate = base
    index = 2

    while True:
        query = Resource.query.filter_by(slug=candidate)
        if resource_id is not None:
            query = query.filter(Resource.id != resource_id)
        if not query.first():
            return candidate
        candidate = f"{base}-{index}"
        index += 1


def get_site_config() -> SiteConfig:
    config = db.session.get(SiteConfig, 1)
    if config is None:
        config = SiteConfig(id=1)
        db.session.add(config)
        db.session.flush()
    return config


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_user_id"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.before_app_request
def load_admin():
    admin_id = session.get("admin_user_id")
    g.admin_user = db.session.get(AdminUser, admin_id) if admin_id else None


def save_upload(file: FileStorage, folder: str) -> str:
    upload_root = current_app.config["UPLOAD_ROOT"]
    target_dir = os.path.join(upload_root, folder)
    os.makedirs(target_dir, exist_ok=True)

    filename = secure_filename(file.filename or "")
    unique_name = f"{uuid.uuid4().hex[:12]}-{filename}"
    file.save(os.path.join(target_dir, unique_name))
    return f"{folder}/{unique_name}"


def save_upload_bytes(content: bytes, filename: str, folder: str) -> str:
    upload_root = current_app.config["UPLOAD_ROOT"]
    target_dir = os.path.join(upload_root, folder)
    os.makedirs(target_dir, exist_ok=True)

    safe_name = secure_filename(os.path.basename(filename)) or "cover-image"
    unique_name = f"{uuid.uuid4().hex[:12]}-{safe_name}"
    full_path = os.path.join(target_dir, unique_name)
    with open(full_path, "wb") as saved_file:
        saved_file.write(content)
    return f"{folder}/{unique_name}"


def remove_uploaded_file(relative_path: str) -> None:
    if not relative_path:
        return
    upload_root = current_app.config["UPLOAD_ROOT"]
    full_path = os.path.abspath(os.path.join(upload_root, relative_path))
    if not full_path.startswith(os.path.abspath(upload_root)):
        return
    if os.path.isfile(full_path):
        os.remove(full_path)


def clean_markdown_text(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^[#>\-\*\+\d\.\s]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_readme_content(readme_text: str, fallback_title: str) -> dict[str, str]:
    lines = readme_text.splitlines()
    title = ""
    headings: list[str] = []
    bullet_points: list[str] = []
    paragraphs: list[str] = []
    buffer: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            if buffer:
                paragraph = clean_markdown_text(" ".join(buffer))
                if paragraph:
                    paragraphs.append(paragraph)
                buffer = []
            continue

        if stripped.startswith("# "):
            if not title:
                title = clean_markdown_text(stripped[2:])
            continue

        if stripped.startswith("## "):
            heading = clean_markdown_text(stripped[3:])
            if heading:
                headings.append(heading)
            continue

        bullet_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        numbered_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if bullet_match or numbered_match:
            bullet_text = clean_markdown_text((bullet_match or numbered_match).group(1))
            if bullet_text:
                bullet_points.append(bullet_text)
            continue

        buffer.append(stripped)

    if buffer:
        paragraph = clean_markdown_text(" ".join(buffer))
        if paragraph:
            paragraphs.append(paragraph)

    safe_title = title or fallback_title or "Imported Resource"
    short_description = paragraphs[0] if paragraphs else f"Imported from {safe_title}."
    overview_parts = paragraphs[:4] or [short_description]
    overview = "\n\n".join(overview_parts)
    highlights = "\n".join(bullet_points[:6])
    tags = "\n".join(headings[:6])

    return {
        "title": safe_title,
        "short_description": short_description[:300],
        "overview": overview,
        "highlights": highlights,
        "tags": tags,
    }


def normalize_relative_name(filename: str) -> str:
    normalized = filename.replace("\\", "/").strip("/")
    parts = [secure_filename(part) for part in PurePosixPath(normalized).parts if part not in {"", ".", ".."}]
    parts = [part for part in parts if part]
    return "/".join(parts)


def cover_candidate_rank(relative_name: str) -> tuple[int, int, str]:
    normalized = relative_name.lower()
    basename = os.path.basename(normalized)
    keyword_rank = 0 if any(hint in basename for hint in COVER_HINTS) else 1
    depth_rank = normalized.count("/")
    return (keyword_rank, depth_rank, basename)


def create_folder_archive(files: list[FileStorage]) -> dict[str, str]:
    upload_root = current_app.config["UPLOAD_ROOT"]
    target_dir = os.path.join(upload_root, "files")
    os.makedirs(target_dir, exist_ok=True)

    valid_files = [file for file in files if file and file.filename]
    if not valid_files:
        raise ValueError("Folder upload is empty.")

    archive_entries: list[tuple[FileStorage, str]] = []
    for file in valid_files:
        relative_name = normalize_relative_name(file.filename or "")
        if not relative_name:
            continue
        archive_entries.append((file, relative_name))

    if not archive_entries:
        raise ValueError("No valid files found in uploaded folder.")

    root_folder = archive_entries[0][1].split("/", 1)[0]
    archive_basename = secure_filename(root_folder) or f"resource-{uuid.uuid4().hex[:8]}"
    archive_name = f"{uuid.uuid4().hex[:12]}-{archive_basename}.zip"
    archive_path = os.path.join(target_dir, archive_name)

    readme_text = ""
    hasher = hashlib.sha256()
    cover_candidate: tuple[tuple[int, int, str], str, bytes] | None = None

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file, relative_name in archive_entries:
            content = file.stream.read()
            file.stream.seek(0)
            archive.writestr(relative_name, content)
            hasher.update(relative_name.encode("utf-8"))
            hasher.update(content)

            lowered_name = relative_name.lower()
            if lowered_name.endswith("/readme.md") or lowered_name == "readme.md":
                try:
                    readme_text = content.decode("utf-8")
                except UnicodeDecodeError:
                    readme_text = content.decode("utf-8", errors="ignore")

            extension = os.path.splitext(lowered_name)[1]
            if extension in IMAGE_EXTENSIONS:
                rank = cover_candidate_rank(relative_name)
                if cover_candidate is None or rank < cover_candidate[0]:
                    cover_candidate = (rank, relative_name, content)

    cover_image_path = ""
    if cover_candidate is not None:
        _, relative_name, content = cover_candidate
        cover_image_path = save_upload_bytes(content, relative_name, "images")

    return {
        "download_path": f"files/{archive_name}",
        "download_name": archive_name,
        "checksum": hasher.hexdigest()[:12].upper(),
        "asset_identifier": f"#{archive_basename.upper()}",
        "folder_name": root_folder,
        "cover_image_path": cover_image_path,
        "file_manifest": "\n".join(relative_name for _, relative_name in archive_entries),
        "readme_text": readme_text,
    }


def resource_from_form(resource: Resource) -> Resource:
    folder_files = request.files.getlist("folder_files")
    folder_payload: dict[str, str] = {}
    readme_payload: dict[str, str] = {}
    if any(file.filename for file in folder_files):
        folder_payload = create_folder_archive(folder_files)
        if folder_payload.get("readme_text"):
            readme_payload = extract_readme_content(
                folder_payload["readme_text"],
                fallback_title=folder_payload.get("folder_name", "Imported Resource"),
            )

    title = request.form.get("title", "").strip() or readme_payload.get("title", "")
    category = request.form.get("category", "").strip() or "Imported"
    short_description = (
        request.form.get("short_description", "").strip()
        or readme_payload.get("short_description", "")
    )
    overview = request.form.get("overview", "").strip() or readme_payload.get("overview", "")

    if not title or not category:
        raise ValueError("Title and category are required.")
    if not short_description or not overview:
        raise ValueError("Short description and overview are required.")

    updated_at_raw = request.form.get("updated_at", "").strip()
    updated_at = (
        datetime.strptime(updated_at_raw, "%Y-%m-%d").date()
        if updated_at_raw
        else china_today()
    )

    custom_slug = request.form.get("slug", "").strip()

    resource.title = title
    resource.slug = unique_slug(custom_slug or title, resource.id)
    resource.resource_code = request.form.get("resource_code", "").strip() or "UNASSIGNED"
    resource.category = category
    resource.short_description = short_description
    resource.overview = overview
    resource.highlights = request.form.get("highlights", "").strip() or readme_payload.get("highlights", "")
    resource.tags = request.form.get("tags", "").strip() or readme_payload.get("tags", "")
    resource.clearance = request.form.get("clearance", "").strip() or "Level 4 Clearance"
    resource.checksum = request.form.get("checksum", "").strip() or folder_payload.get("checksum", "N/A")
    resource.asset_identifier = request.form.get("asset_identifier", "").strip() or folder_payload.get("asset_identifier", "N/A")
    if "image_url" in request.form:
        resource.image_url = request.form.get("image_url", "").strip()
    resource.cloud_link = request.form.get("cloud_link", "").strip()
    resource.cloud_code = request.form.get("cloud_code", "").strip()
    resource.download_name = folder_payload.get("download_name", resource.download_name)
    resource.file_manifest = folder_payload.get("file_manifest", resource.file_manifest)
    resource.readme_content = folder_payload.get("readme_text", resource.readme_content)
    resource.status = request.form.get("status", "").strip() or "ONLINE_READY"
    resource.display_order = request.form.get("display_order", type=int, default=0)
    resource.updated_at = updated_at

    if folder_payload.get("cover_image_path"):
        remove_uploaded_file(resource.image_path)
        resource.image_path = folder_payload["cover_image_path"]
        resource.image_url = ""

    image_file = request.files.get("image_file")
    if image_file and image_file.filename:
        remove_uploaded_file(resource.image_path)
        resource.image_path = save_upload(image_file, "images")
        resource.image_url = ""

    download_file = request.files.get("download_file")
    if folder_payload.get("download_path"):
        remove_uploaded_file(resource.download_path)
        resource.download_path = folder_payload["download_path"]
    elif download_file and download_file.filename:
        remove_uploaded_file(resource.download_path)
        resource.download_path = save_upload(download_file, "files")
        resource.download_name = os.path.basename(resource.download_path)

    return resource


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_user_id"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        admin = AdminUser.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            session.clear()
            session["admin_user_id"] = admin.id
            flash("Login successful.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("admin/login.html")


@bp.route("/logout")
@admin_required
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("admin.login"))


@bp.route("/")
@admin_required
def dashboard():
    keyword = request.args.get("q", "").strip()
    query = Resource.query
    if keyword:
        wildcard = f"%{keyword}%"
        query = query.filter(
            or_(
                Resource.title.ilike(wildcard),
                Resource.category.ilike(wildcard),
                Resource.resource_code.ilike(wildcard),
            )
        )

    resources = query.order_by(Resource.created_at.desc(), Resource.id.desc()).all()
    return render_template("admin/dashboard.html", resources=resources, keyword=keyword)


@bp.route("/site-settings", methods=["GET", "POST"])
@admin_required
def site_settings():
    config = get_site_config()

    if request.method == "POST":
        config.left_title = request.form.get("left_title", "").strip()
        config.left_subtitle = request.form.get("left_subtitle", "").strip()
        config.right_title = request.form.get("right_title", "").strip()
        config.right_subtitle = request.form.get("right_subtitle", "").strip()

        left_qr_file = request.files.get("left_qr_file")
        if left_qr_file and left_qr_file.filename:
            remove_uploaded_file(config.left_qr_path)
            config.left_qr_path = save_upload(left_qr_file, "images")

        right_qr_file = request.files.get("right_qr_file")
        if right_qr_file and right_qr_file.filename:
            remove_uploaded_file(config.right_qr_path)
            config.right_qr_path = save_upload(right_qr_file, "images")

        db.session.commit()
        flash("二维码配置已保存。", "success")
        return redirect(url_for("admin.site_settings"))

    return render_template("admin/site_settings.html", config=config)


@bp.route("/resources/new", methods=["GET", "POST"])
@admin_required
def create_resource():
    resource = Resource(
        title="",
        slug="",
        resource_code="",
        category="",
        short_description="",
        overview="",
        highlights="",
        tags="",
        image_url="",
        download_url="",
        cloud_link="",
        cloud_code="",
    )

    if request.method == "POST":
        try:
            resource_from_form(resource)
            db.session.add(resource)
            db.session.commit()
            flash("Resource created.", "success")
            return redirect(url_for("admin.dashboard"))
        except ValueError as exc:
            flash(str(exc), "error")

    return render_template("admin/resource_form.html", resource=resource, form_mode="create")


@bp.route("/resources/<int:resource_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_resource(resource_id: int):
    resource = Resource.query.get_or_404(resource_id)

    if request.method == "POST":
        try:
            resource_from_form(resource)
            db.session.commit()
            flash("Resource updated.", "success")
            return redirect(url_for("admin.dashboard"))
        except ValueError as exc:
            flash(str(exc), "error")

    return render_template("admin/resource_form.html", resource=resource, form_mode="edit")


@bp.route("/resources/<int:resource_id>/delete", methods=["POST"])
@admin_required
def delete_resource(resource_id: int):
    resource = Resource.query.get_or_404(resource_id)
    remove_uploaded_file(resource.image_path)
    remove_uploaded_file(resource.download_path)
    db.session.delete(resource)
    db.session.commit()
    flash(f'Resource "{resource.title}" deleted.', "success")
    return redirect(url_for("admin.dashboard"))

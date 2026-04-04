from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
CHINA_TZ = timezone(timedelta(hours=8))


def china_now() -> datetime:
    return datetime.now(CHINA_TZ).replace(tzinfo=None)


def china_today() -> date:
    return china_now().date()


def strip_markdown_formatting(value: str) -> str:
    text = value.strip().strip("#").strip()
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def build_anchor_id(value: str, used: set[str] | None = None) -> str:
    anchor = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.lower()).strip("-")
    anchor = re.sub(r"-{2,}", "-", anchor) or "section"
    if used is None:
        return anchor

    candidate = anchor
    index = 2
    while candidate in used:
        candidate = f"{anchor}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def extract_readme_sections(markdown_text: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    used: set[str] = set()

    for line in markdown_text.splitlines():
        match = HEADING_RE.match(line.strip())
        if not match:
            continue
        title = strip_markdown_formatting(match.group(2))
        if not title:
            continue
        sections.append({"title": title, "id": build_anchor_id(title, used)})

    return sections


def inject_readme_heading_anchors(markdown_text: str) -> str:
    lines: list[str] = []
    used: set[str] = set()

    for line in markdown_text.splitlines():
        match = HEADING_RE.match(line.strip())
        if not match:
            lines.append(line)
            continue

        hashes, raw_title = match.groups()
        title = strip_markdown_formatting(raw_title)
        if not title:
            lines.append(line)
            continue

        anchor_id = build_anchor_id(title, used)
        lines.append(f"{hashes} {raw_title} {{#{anchor_id}}}")

    return "\n".join(lines)


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=china_now, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class SiteConfig(db.Model):
    __tablename__ = "site_config"

    id = db.Column(db.Integer, primary_key=True)
    left_qr_path = db.Column(db.String(255), default="", nullable=False)
    left_title = db.Column(db.String(120), default="", nullable=False)
    left_subtitle = db.Column(db.String(255), default="", nullable=False)
    right_qr_path = db.Column(db.String(255), default="", nullable=False)
    right_title = db.Column(db.String(120), default="", nullable=False)
    right_subtitle = db.Column(db.String(255), default="", nullable=False)
    created_at = db.Column(db.DateTime, default=china_now, nullable=False)
    modified_at = db.Column(
        db.DateTime, default=china_now, onupdate=china_now, nullable=False
    )


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    resource_code = db.Column(db.String(40), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    short_description = db.Column(db.Text, nullable=False)
    overview = db.Column(db.Text, nullable=False)
    highlights = db.Column(db.Text, default="", nullable=False)
    tags = db.Column(db.Text, default="", nullable=False)
    clearance = db.Column(db.String(80), default="Level 4 Clearance", nullable=False)
    checksum = db.Column(db.String(80), default="N/A", nullable=False)
    asset_identifier = db.Column(db.String(80), default="N/A", nullable=False)
    image_url = db.Column(db.Text, default="", nullable=False)
    image_path = db.Column(db.String(255), default="", nullable=False)
    download_url = db.Column(db.Text, default="", nullable=False)
    cloud_link = db.Column(db.Text, default="", nullable=False)
    cloud_code = db.Column(db.String(80), default="", nullable=False)
    download_path = db.Column(db.String(255), default="", nullable=False)
    download_name = db.Column(db.String(255), default="", nullable=False)
    file_manifest = db.Column(db.Text, default="", nullable=False)
    readme_content = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(40), default="ONLINE_READY", nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.Date, default=china_today, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=china_now, nullable=False)
    modified_at = db.Column(
        db.DateTime, default=china_now, onupdate=china_now, nullable=False
    )

    @property
    def tag_list(self) -> list[str]:
        return [item.strip() for item in self.tags.splitlines() if item.strip()]

    @property
    def highlight_list(self) -> list[str]:
        return [item.strip() for item in self.highlights.splitlines() if item.strip()]

    @property
    def overview_paragraphs(self) -> list[str]:
        blocks = [item.strip() for item in self.overview.split("\n\n") if item.strip()]
        return blocks or [self.overview.strip()]

    @property
    def manifest_list(self) -> list[str]:
        return [item.strip() for item in self.file_manifest.splitlines() if item.strip()]

    @property
    def download_display_name(self) -> str:
        if self.download_name:
            return self.download_name
        if self.download_path:
            return self.download_path.split("/")[-1]
        return ""

    @property
    def has_cloud_link(self) -> bool:
        return bool(self.resolved_cloud_link)

    @property
    def resolved_cloud_link(self) -> str:
        return (self.cloud_link or self.download_url or "").strip()

    @property
    def has_archive(self) -> bool:
        return bool((self.download_path or "").strip())

    @property
    def readme_sections(self) -> list[dict[str, str]]:
        return extract_readme_sections(self.readme_content or "")

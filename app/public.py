from __future__ import annotations

import html
import os
from urllib.parse import urlencode

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from markupsafe import Markup
from sqlalchemy import or_

from .models import Resource, SiteConfig, inject_readme_heading_anchors

try:
    import bleach
except ImportError:  # pragma: no cover - optional runtime fallback
    bleach = None

try:
    import markdown
except ImportError:  # pragma: no cover - optional runtime fallback
    markdown = None


bp = Blueprint("public", __name__)
HOMEPAGE_URL = "https://scor.vip"

ALLOWED_TAGS = (list(bleach.sanitizer.ALLOWED_TAGS) if bleach else []) + [
    "p",
    "pre",
    "code",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "br",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "blockquote",
]

ALLOWED_ATTRIBUTES = {
    **(bleach.sanitizer.ALLOWED_ATTRIBUTES if bleach else {}),
    "a": ["href", "title", "target", "rel"],
    "code": ["class"],
    "h1": ["id"],
    "h2": ["id"],
    "h3": ["id"],
    "h4": ["id"],
    "h5": ["id"],
    "h6": ["id"],
}


TRANSLATIONS = {
    "zh": {
        "site_title": "\u8d44\u6e90\u76ee\u5f55",
        "nav_directory": "\u76ee\u5f55",
        "nav_resources": "\u8d44\u6e90",
        "nav_admin": "\u9996\u9875",
        "search_placeholder": "\u641c\u7d22\u8d44\u6e90\u5e93...",
        "hero_label": "\u7cfb\u7edf\u65e5\u5fd7 // \u4e2d\u592e\u8d44\u6e90\u5e93",
        "hero_title_line_1": "\u8d44\u6e90",
        "hero_title_line_2": "\u76ee\u5f55",
        "hero_desc": "\u8bbf\u95ee\u9ad8\u8d28\u91cf\u5de5\u7a0b\u8d44\u4ea7\u3001\u6280\u672f\u6587\u6863\u4e0e\u57fa\u7840\u8bbe\u65bd\u84dd\u56fe\uff0c\u4e3a\u4e2a\u4eba\u77e5\u8bc6\u5e93\u4e0e\u8d44\u6e90\u5c55\u793a\u800c\u8bbe\u8ba1\u3002",
        "status": "\u72b6\u6001\uff1a",
        "status_value": "\u5728\u7ebf\u5c31\u7eea",
        "filter_by": "\u7b5b\u9009\uff1a",
        "all_systems": "\u5168\u90e8\u5206\u7c7b",
        "matches": "\u5339\u914d\u6570\uff1a",
        "last_update": "\u66f4\u65b0\u65e5\u671f",
        "view_details": "\u67e5\u770b\u8be6\u60c5",
        "no_resource_label": "\u6682\u65e0\u8d44\u6e90",
        "no_resource_title": "\u6ca1\u6709\u5339\u914d\u7684\u8d44\u6e90\u6761\u76ee",
        "no_resource_desc": "\u8bf7\u8c03\u6574\u5173\u952e\u8bcd\u6216\u5206\u7c7b\u7b5b\u9009\uff0c\u4e5f\u53ef\u4ee5\u5230\u540e\u53f0\u65b0\u589e\u8d44\u6e90\u3002",
        "footer_core": "\u6838\u5fc3",
        "footer_docs": "\u6587\u6863",
        "footer_terminal": "\u7ec8\u7aef",
        "footer_network": "\u7f51\u7edc",
        "footer_security": "\u5b89\u5168",
        "footer_resources": "\u8d44\u6e90",
        "footer_encryption": "\u52a0\u5bc6",
        "footer_vault": "\u9996\u9875",
        "footer_mobile_sync": "\u79fb\u52a8\u540c\u6b65",
        "footer_mobile_sub": "\u8fde\u63a5\u5b89\u5168\u8bbe\u5907",
        "footer_access_node": "\u8bbf\u95ee\u8282\u70b9 ALPHA",
        "footer_access_sub": "\u52a0\u5bc6\u63e1\u624b",
        "footer_copyright": "2026 \u6570\u5b57\u5b9e\u9a8c\u5ba4 \u7248\u6743\u6240\u6709",
        "footer_beian": "\u82cfICP\u59072022040643\u53f7-1",
        "detail_header": "\u7cfb\u7edf\u6838\u5fc3\u8d44\u6e90",
        "detail_overview": "\u6587\u6863\u6982\u89c8",
        "detail_download": "\u4e0b\u8f7d\u8d44\u6e90",
        "detail_remote_access": "\u8bbf\u95ee\u9996\u9875",
        "asset_id": "\u8d44\u6e90\u7f16\u53f7",
        "checksum": "\u6821\u9a8c\u503c",
        "detail_package": "\u4e0b\u8f7d\u5305",
        "detail_filename": "\u6587\u4ef6\u540d",
        "detail_filelist": "\u5305\u5185\u6587\u4ef6",
        "detail_cloud": "\u4e91\u76d8\u4e0b\u8f7d",
        "detail_cloud_link": "\u4e91\u76d8\u94fe\u63a5",
        "detail_cloud_code": "\u53d6\u4ef6\u7801",
        "detail_readme_full": "README \u5168\u6587",
        "detail_quick_view": "\u5185\u5bb9\u6458\u8981",
        "detail_download_zip": "\u4e0b\u8f7d ZIP",
        "detail_open_cloud": "\u6253\u5f00\u4e91\u76d8",
    },
    "en": {
        "site_title": "Resource Directory",
        "nav_directory": "DIRECTORY",
        "nav_resources": "RESOURCES",
        "nav_admin": "HOME",
        "search_placeholder": "QUERY DATABASE...",
        "hero_label": "SYSTEM.LOG // CENTRAL_REPOSITORY",
        "hero_title_line_1": "Resource",
        "hero_title_line_2": "Directory.",
        "hero_desc": "Access high-fidelity engineering assets, neural documentation, and infrastructure blueprints for a personal curated resource hub.",
        "status": "STATUS:",
        "status_value": "ONLINE_READY",
        "filter_by": "FILTER_BY:",
        "all_systems": "All Systems",
        "matches": "MATCHES:",
        "last_update": "LAST_UPDATE",
        "view_details": "VIEW DETAILS",
        "no_resource_label": "NO_RESOURCE_FOUND",
        "no_resource_title": "No matching resource entry.",
        "no_resource_desc": "Adjust the keyword or category filter in the command surface above. New resources can be created in the admin dashboard.",
        "footer_core": "CORE",
        "footer_docs": "DOCUMENTATION",
        "footer_terminal": "TERMINAL",
        "footer_network": "NETWORK",
        "footer_security": "SECURITY",
        "footer_resources": "RESOURCES",
        "footer_encryption": "ENCRYPTION",
        "footer_vault": "HOME",
        "footer_mobile_sync": "MOBILE_SYNC",
        "footer_mobile_sub": "LINK_SECURE_DEVICE",
        "footer_access_node": "ACCESS_NODE_ALPHA",
        "footer_access_sub": "ENCRYPTED_HANDSHAKE",
        "footer_copyright": "2026 THE DIGITAL LABORATORY. ALL RIGHTS RESERVED.",
        "footer_beian": "Su ICP 2022040643-1",
        "detail_header": "System.Core.Resource",
        "detail_overview": "Documentation_Overview",
        "detail_download": "Download Resource",
        "detail_remote_access": "Visit Homepage",
        "asset_id": "Asset_ID",
        "checksum": "Checksum",
        "detail_package": "Download Package",
        "detail_filename": "Filename",
        "detail_filelist": "Package Files",
        "detail_cloud": "Cloud Drive",
        "detail_cloud_link": "Cloud Link",
        "detail_cloud_code": "Access Code",
        "detail_readme_full": "Full README",
        "detail_quick_view": "Quick Summary",
        "detail_download_zip": "Download ZIP",
        "detail_open_cloud": "Open Cloud Drive",
    },
}


def get_lang() -> str:
    lang = session.get("lang", "zh")
    return lang if lang in TRANSLATIONS else "zh"


def t(key: str) -> str:
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def render_markdown(value: str) -> Markup:
    if not value.strip():
        return Markup("")

    if markdown is None or bleach is None:
        escaped = html.escape(value)
        return Markup(
            f'<pre class="whitespace-pre-wrap break-words text-sm font-light leading-7 text-on-surface-variant">{escaped}</pre>'
        )

    rendered = markdown.markdown(
        inject_readme_heading_anchors(value),
        extensions=[
            "attr_list",
            "fenced_code",
            "tables",
            "sane_lists",
            "nl2br",
        ],
        output_format="html5",
    )
    cleaned = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=bleach.sanitizer.ALLOWED_PROTOCOLS,
        strip=True,
    )
    linked = bleach.linkify(cleaned)
    return Markup(linked)


def build_query_url(**updates: object) -> str:
    params = request.args.to_dict(flat=True)
    for key, value in updates.items():
        if value in (None, "", False):
            params.pop(key, None)
        else:
            params[key] = value
    query_string = urlencode(params)
    base = url_for("public.index")
    return f"{base}?{query_string}" if query_string else base


def get_site_config() -> SiteConfig:
    config = SiteConfig.query.get(1)
    if config is not None:
        return config

    return SiteConfig(
        id=1,
        left_title=t("footer_access_node"),
        left_subtitle=t("footer_access_sub"),
        right_title=t("footer_mobile_sync"),
        right_subtitle=t("footer_mobile_sub"),
    )


@bp.app_context_processor
def inject_public_i18n():
    return {
        "t": t,
        "current_lang": get_lang(),
        "render_markdown": render_markdown,
        "homepage_url": HOMEPAGE_URL,
        "site_config": get_site_config(),
    }


@bp.route("/set-language/<lang>")
def set_language(lang: str):
    if lang in TRANSLATIONS:
        session["lang"] = lang

    next_url = request.args.get("next", "").strip()
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("public.index"))


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = max(request.args.get("page", default=1, type=int), 1)
    detail_slug = request.args.get("detail", "").strip()

    resource_query = Resource.query

    if q:
        wildcard = f"%{q}%"
        resource_query = resource_query.filter(
            or_(
                Resource.title.ilike(wildcard),
                Resource.short_description.ilike(wildcard),
                Resource.category.ilike(wildcard),
                Resource.tags.ilike(wildcard),
            )
        )

    if category:
        resource_query = resource_query.filter(Resource.category == category)

    ordered_query = resource_query.order_by(Resource.created_at.desc(), Resource.id.desc())
    total_matches = ordered_query.count()
    pagination = ordered_query.paginate(page=page, per_page=5, error_out=False)

    detail_resource = None
    if detail_slug:
        detail_resource = Resource.query.filter_by(slug=detail_slug).first()

    categories = [
        value[0]
        for value in Resource.query.with_entities(Resource.category)
        .distinct()
        .order_by(Resource.category.asc())
        .all()
    ]

    return render_template(
        "public/index.html",
        resources=pagination.items,
        pagination=pagination,
        total_matches=total_matches,
        categories=categories,
        active_category=category,
        search_query=q,
        detail_resource=detail_resource,
        query_url=build_query_url,
    )


@bp.route("/media/<path:path>")
def media(path: str):
    return send_from_directory(current_app.config["UPLOAD_ROOT"], path)


@bp.route("/resources/<slug>/download")
def download(slug: str):
    resource = Resource.query.filter_by(slug=slug).first_or_404()

    if resource.download_path:
        directory = current_app.config["UPLOAD_ROOT"]
        filename = os.path.basename(resource.download_path)
        return send_from_directory(
            directory,
            resource.download_path,
            as_attachment=True,
            download_name=resource.download_name or filename,
        )

    if resource.cloud_link:
        return redirect(resource.cloud_link)

    if resource.download_url:
        return redirect(resource.download_url)

    return redirect(url_for("public.index", detail=slug))

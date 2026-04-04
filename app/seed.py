from __future__ import annotations

import os
import zipfile
from datetime import date

from flask import current_app
from sqlalchemy import inspect, text

from .extensions import db
from .models import AdminUser, Resource, SiteConfig


DEFAULT_ADMIN_USERNAME = "cjwcjw"
DEFAULT_ADMIN_PASSWORD = "19911017"

DEFAULT_IMAGE = (
    "https://images.unsplash.com/photo-1516321318423-f06f85e504b3"
    "?auto=format&fit=crop&w=900&q=80"
)

DEFAULT_RESOURCES = [
    {
        "title": "Advanced AI Implementation Guide",
        "slug": "advanced-ai-implementation-guide",
        "resource_code": "AX-7740",
        "category": "Implementation",
        "short_description": "Architectural blueprints for deploying large-scale neural transformers within decentralized satellite networks.",
        "overview": (
            "This comprehensive architectural framework outlines the core methodologies for deploying large-scale heuristic "
            "models within synthetic environments. Designed for engineers operating at the frontier of digital synthesis, "
            "this guide covers the critical synchronization protocols required for low-latency inference cycles.\n\n"
            "The documentation delves deep into multi-threaded vector processing, tensor quantization strategies, and "
            "autonomous error-correction loops. It serves as the primary technical anchor for all neural infrastructure "
            "projects within the Laboratory."
        ),
        "highlights": "\n".join(
            [
                "Full schematic breakdown of Layer 3 neural architectures.",
                "Performance benchmarks for Real-Time data ingestion.",
                "End-to-end encryption protocols for weight transmission.",
            ]
        ),
        "tags": "\n".join(["Deep Learning", "Neural Ops"]),
        "clearance": "Level 4 Clearance",
        "checksum": "7F4A...B2C1",
        "asset_identifier": "#AI-IMPL-992-X",
        "image_url": DEFAULT_IMAGE,
        "status": "ONLINE_READY",
        "display_order": 1,
        "updated_at": date(2024, 10, 12),
    },
    {
        "title": "Quantum Entropy Harvesting Protocols",
        "slug": "quantum-entropy-harvesting-protocols",
        "resource_code": "QS-9011",
        "category": "Quantum",
        "short_description": "Standard operating procedures for capturing and distilling chaotic quantum noise into usable encryption entropy.",
        "overview": (
            "A field-tested operating model for extracting high-grade entropy from unstable quantum noise sources across "
            "distributed hardware arrays.\n\n"
            "The protocol balances signal isolation, redundancy, and cryptographic sealing requirements for secure "
            "infrastructure projects."
        ),
        "highlights": "\n".join(
            [
                "Noise capture workflow for distributed quantum hardware.",
                "Validation baselines for entropy quality assurance.",
                "Key rotation strategies for secure downstream consumption.",
            ]
        ),
        "tags": "\n".join(["Quantum Systems", "Encryption"]),
        "clearance": "Level 3 Clearance",
        "checksum": "51D0...C88A",
        "asset_identifier": "#QENT-201-A",
        "image_url": DEFAULT_IMAGE,
        "status": "ONLINE_READY",
        "display_order": 2,
        "updated_at": date(2024, 11, 1),
    },
    {
        "title": "Low-Orbit Satellite Mesh Topology",
        "slug": "low-orbit-satellite-mesh-topology",
        "resource_code": "NL-2234",
        "category": "Satellite",
        "short_description": "Comprehensive routing tables and physical layer requirements for secondary orbital communication meshes.",
        "overview": (
            "This topology bundle documents the routing, fault tolerance, and relay geometry needed to maintain resilient "
            "communications across low-orbit nodes.\n\n"
            "It combines orbital constraints with mesh failover logic so teams can reason about deployment at system scale."
        ),
        "highlights": "\n".join(
            [
                "Mesh routing patterns for low-latency orbital relay.",
                "Physical layer constraints across harsh environments.",
                "Fallback scenarios for node-level outages.",
            ]
        ),
        "tags": "\n".join(["Satellite", "Infrastructure"]),
        "clearance": "Level 2 Clearance",
        "checksum": "A4CC...912E",
        "asset_identifier": "#SAT-MESH-342",
        "image_url": DEFAULT_IMAGE,
        "status": "ONLINE_READY",
        "display_order": 3,
        "updated_at": date(2024, 9, 28),
    },
    {
        "title": "Synthetic Vault Access Framework",
        "slug": "synthetic-vault-access-framework",
        "resource_code": "EN-0041",
        "category": "Encryption",
        "short_description": "Identity provider integration schemas for biometric and neural-pattern authentication layers.",
        "overview": (
            "A secure access framework for teams building identity-aware vault systems with biometric and neural-pattern "
            "signals.\n\n"
            "It maps policy layers, trust boundaries, and storage isolation patterns used in highly controlled environments."
        ),
        "highlights": "\n".join(
            [
                "Identity provider integration reference architecture.",
                "Neural-pattern authentication safeguards.",
                "Vault segmentation and policy inheritance rules.",
            ]
        ),
        "tags": "\n".join(["Security", "Vault"]),
        "clearance": "Level 5 Clearance",
        "checksum": "C10D...88FA",
        "asset_identifier": "#VAULT-EN-41",
        "image_url": DEFAULT_IMAGE,
        "status": "ONLINE_READY",
        "display_order": 4,
        "updated_at": date(2024, 11, 15),
    },
    {
        "title": "Cognitive Load Balancing Utility",
        "slug": "cognitive-load-balancing-utility",
        "resource_code": "NU-1100",
        "category": "Neural",
        "short_description": "Real-time distribution algorithms for offloading heavy inference tasks across idle neural clusters.",
        "overview": (
            "A real-time balancing toolkit for redistributing intensive inference tasks across underutilized neural clusters.\n\n"
            "The resource focuses on cluster health signals, queue shaping, and fairness strategies under burst load."
        ),
        "highlights": "\n".join(
            [
                "Cluster-aware task redistribution heuristics.",
                "Queue shaping for bursty inference workloads.",
                "Operational safeguards for graceful degradation.",
            ]
        ),
        "tags": "\n".join(["Neural", "Optimization"]),
        "clearance": "Level 4 Clearance",
        "checksum": "D921...17B0",
        "asset_identifier": "#NEURAL-LOAD-1100",
        "image_url": DEFAULT_IMAGE,
        "status": "ONLINE_READY",
        "display_order": 5,
        "updated_at": date(2024, 11, 18),
    },
]

DEFAULT_SITE_CONFIG = {
    "left_title": "访问节点 ALPHA",
    "left_subtitle": "加密握手",
    "right_title": "移动同步",
    "right_subtitle": "连接安全设备",
}


def ensure_seed_data() -> None:
    db.create_all()
    ensure_resource_schema()

    admin = AdminUser.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    if not admin:
        admin = AdminUser(username=DEFAULT_ADMIN_USERNAME)
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)

    if Resource.query.count() == 0:
        for payload in DEFAULT_RESOURCES:
            db.session.add(Resource(**payload))

    site_config = db.session.get(SiteConfig, 1)
    if not site_config:
        db.session.add(SiteConfig(id=1, **DEFAULT_SITE_CONFIG))

    backfill_resource_archives()
    backfill_cloud_links()
    db.session.commit()


def ensure_resource_schema() -> None:
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("resources")}
    statements: list[str] = []
    legacy_columns = {"file_size", "file_format"}

    if legacy_columns & columns:
        rebuild_resources_table_without_legacy_columns(columns)
        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("resources")}

    if "download_name" not in columns:
        statements.append("ALTER TABLE resources ADD COLUMN download_name VARCHAR(255) NOT NULL DEFAULT ''")
    if "cloud_link" not in columns:
        statements.append("ALTER TABLE resources ADD COLUMN cloud_link TEXT NOT NULL DEFAULT ''")
    if "cloud_code" not in columns:
        statements.append("ALTER TABLE resources ADD COLUMN cloud_code VARCHAR(80) NOT NULL DEFAULT ''")
    if "file_manifest" not in columns:
        statements.append("ALTER TABLE resources ADD COLUMN file_manifest TEXT NOT NULL DEFAULT ''")
    if "readme_content" not in columns:
        statements.append("ALTER TABLE resources ADD COLUMN readme_content TEXT NOT NULL DEFAULT ''")

    for statement in statements:
        db.session.execute(text(statement))

    if statements:
        db.session.commit()


def rebuild_resources_table_without_legacy_columns(existing_columns: set[str]) -> None:
    keep_columns = [
        "id",
        "title",
        "slug",
        "resource_code",
        "category",
        "short_description",
        "overview",
        "highlights",
        "tags",
        "clearance",
        "checksum",
        "asset_identifier",
        "image_url",
        "image_path",
        "download_url",
        "cloud_link",
        "cloud_code",
        "download_path",
        "download_name",
        "file_manifest",
        "readme_content",
        "status",
        "display_order",
        "updated_at",
        "created_at",
        "modified_at",
    ]
    present_columns = [column for column in keep_columns if column in existing_columns]
    column_sql = ", ".join(present_columns)

    db.session.execute(text("DROP INDEX IF EXISTS ix_resources_slug"))
    db.session.execute(text("DROP INDEX IF EXISTS ix_resources_category"))
    db.session.execute(text("DROP INDEX IF EXISTS ix_resources_updated_at"))
    db.session.execute(text("ALTER TABLE resources RENAME TO resources_old"))
    db.session.execute(
        text(
            """
            CREATE TABLE resources (
                id INTEGER NOT NULL PRIMARY KEY,
                title VARCHAR(160) NOT NULL,
                slug VARCHAR(180) NOT NULL,
                resource_code VARCHAR(40) NOT NULL,
                category VARCHAR(80) NOT NULL,
                short_description TEXT NOT NULL,
                overview TEXT NOT NULL,
                highlights TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                clearance VARCHAR(80) NOT NULL DEFAULT 'Level 4 Clearance',
                checksum VARCHAR(80) NOT NULL DEFAULT 'N/A',
                asset_identifier VARCHAR(80) NOT NULL DEFAULT 'N/A',
                image_url TEXT NOT NULL DEFAULT '',
                image_path VARCHAR(255) NOT NULL DEFAULT '',
                download_url TEXT NOT NULL DEFAULT '',
                cloud_link TEXT NOT NULL DEFAULT '',
                cloud_code VARCHAR(80) NOT NULL DEFAULT '',
                download_path VARCHAR(255) NOT NULL DEFAULT '',
                download_name VARCHAR(255) NOT NULL DEFAULT '',
                file_manifest TEXT NOT NULL DEFAULT '',
                readme_content TEXT NOT NULL DEFAULT '',
                status VARCHAR(40) NOT NULL DEFAULT 'ONLINE_READY',
                display_order INTEGER NOT NULL DEFAULT 0,
                updated_at DATE NOT NULL,
                created_at DATETIME NOT NULL,
                modified_at DATETIME NOT NULL
            )
            """
        )
    )
    db.session.execute(
        text(f"INSERT INTO resources ({column_sql}) SELECT {column_sql} FROM resources_old")
    )
    db.session.execute(text("DROP TABLE resources_old"))
    db.session.execute(text("CREATE UNIQUE INDEX ix_resources_slug ON resources (slug)"))
    db.session.execute(text("CREATE INDEX ix_resources_category ON resources (category)"))
    db.session.execute(text("CREATE INDEX ix_resources_updated_at ON resources (updated_at)"))
    db.session.commit()


def backfill_resource_archives() -> None:
    upload_root = current_app.config["UPLOAD_ROOT"]
    updated = False

    resources = Resource.query.filter(Resource.download_path != "").all()
    for resource in resources:
        needs_backfill = not (
            resource.download_name and resource.file_manifest and resource.readme_content
        )
        if not needs_backfill:
            continue

        archive_path = os.path.abspath(os.path.join(upload_root, resource.download_path))
        if not os.path.isfile(archive_path) or not archive_path.lower().endswith(".zip"):
            if not resource.download_name and resource.download_path:
                resource.download_name = os.path.basename(resource.download_path)
                updated = True
            continue

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                file_names = sorted(
                    name for name in archive.namelist() if name and not name.endswith("/")
                )
                readme_text = ""
                for name in file_names:
                    lowered = name.lower()
                    if lowered.endswith("/readme.md") or lowered == "readme.md":
                        raw = archive.read(name)
                        try:
                            readme_text = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            readme_text = raw.decode("utf-8", errors="ignore")
                        break

                if not resource.download_name:
                    resource.download_name = os.path.basename(resource.download_path)
                if not resource.file_manifest:
                    resource.file_manifest = "\n".join(file_names)
                if readme_text and not resource.readme_content:
                    resource.readme_content = readme_text
                updated = True
        except zipfile.BadZipFile:
            if not resource.download_name:
                resource.download_name = os.path.basename(resource.download_path)
                updated = True

    if updated:
        db.session.commit()


def backfill_cloud_links() -> None:
    updated = False

    for resource in Resource.query.all():
        if resource.cloud_link or not resource.download_url:
            continue
        resource.cloud_link = resource.download_url
        updated = True

    if updated:
        db.session.commit()

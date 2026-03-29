from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent / "backend"
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
MIGRATIONS_ENV = BACKEND_ROOT / "migrations" / "env.py"
VERSION_DIR = BACKEND_ROOT / "migrations" / "versions"
MODEL_DIR = BACKEND_ROOT / "app" / "models"


EXPECTED_MIGRATION_TARGETS = {
    "users",
    "roles",
    "activity_logs",
    "areas",
    "feature_areas",
    "news_articles",
    "wiki_pages",
    "forum_categories",
    "forum_threads",
    "forum_posts",
    "notifications",
    "game_characters",
    "game_save_slots",
    "game_experience_templates",
}


class TestMigrationAndModelFiles:
    def test_alembic_files_exist(self):
        assert ALEMBIC_INI.exists(), "alembic.ini must exist"
        assert MIGRATIONS_ENV.exists(), "migrations/env.py must exist"
        assert VERSION_DIR.exists() and VERSION_DIR.is_dir(), "migrations/versions must exist"

    def test_alembic_ini_contains_required_core_settings(self):
        content = ALEMBIC_INI.read_text(encoding="utf-8")
        assert "script_location =" in content
        assert "prepend_sys_path = ." in content

    def test_repository_contains_real_migration_version_files(self):
        migration_files = sorted(VERSION_DIR.glob("*.py"))
        assert migration_files, "expected at least one migration file"
        assert any(path.name.startswith("001_") for path in migration_files)

    def test_migration_files_are_parseable_python(self):
        migration_files = sorted(VERSION_DIR.glob("*.py"))
        assert migration_files, "expected at least one migration file"
        for path in migration_files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_each_migration_file_defines_revision_and_upgrade_downgrade(self):
        for path in sorted(VERSION_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            assignments = {}
            functions = set()
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            assignments[target.id] = ast.unparse(node.value)
                elif isinstance(node, ast.FunctionDef):
                    functions.add(node.name)

            assert "revision" in assignments, f"{path.name} missing revision"
            assert "down_revision" in assignments, f"{path.name} missing down_revision"
            assert "upgrade" in functions, f"{path.name} missing upgrade()"
            assert "downgrade" in functions, f"{path.name} missing downgrade()"

    def test_migration_revisions_are_unique(self):
        revisions = []
        for path in sorted(VERSION_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "revision":
                            if isinstance(node.value, ast.Constant):
                                revisions.append(node.value.value)
        assert revisions
        assert len(revisions) == len(set(revisions)), "migration revision ids must be unique"

    def test_migration_chain_mentions_current_major_tables(self):
        migration_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(VERSION_DIR.glob("*.py")))
        for table_name in EXPECTED_MIGRATION_TARGETS:
            assert table_name in migration_text, f"migration history should mention {table_name}"

    def test_model_files_are_parseable_python(self):
        model_files = sorted(path for path in MODEL_DIR.glob("*.py") if path.name != "__init__.py")
        assert model_files
        for path in model_files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_model_registry_exports_current_database_models(self):
        init_content = (MODEL_DIR / "__init__.py").read_text(encoding="utf-8")
        expected_exports = [
            "ActivityLog",
            "Area",
            "FeatureArea",
            "Role",
            "User",
            "PasswordResetToken",
            "EmailVerificationToken",
            "TokenBlacklist",
            "RefreshToken",
            "NewsArticle",
            "WikiPage",
            "Slogan",
            "SiteSetting",
            "Notification",
            "GameCharacter",
            "GameSaveSlot",
            "GameExperienceTemplate",
            "ForumCategory",
            "ForumThread",
            "ForumPost",
            "ForumPostLike",
            "ForumReport",
            "ForumThreadSubscription",
            "ForumThreadBookmark",
            "ForumTag",
            "ForumThreadTag",
            "ModeratorAssignment",
        ]
        for export_name in expected_exports:
            assert export_name in init_content

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import configure_mappers

from app.db.models import Base


def test_erd_tables_are_registered() -> None:
    expected_tables = {
        "users",
        "llm_models",
        "prompts",
        "styles",
        "posts",
        "post_versions",
        "images",
        "telegram_messages",
        "schedules",
        "linkedin_accounts",
        "publish_history",
        "profile_optimizations",
        "cv_documents",
        "job_listings",
        "job_matches",
        "settings",
        "workflow_executions",
        "workflow_node_executions",
        "workflow_actions",
    }

    assert set(Base.metadata.tables) == expected_tables


def test_models_configure_and_foreign_keys_exist() -> None:
    configure_mappers()

    foreign_key_count = sum(
        sum(isinstance(constraint, ForeignKeyConstraint) for constraint in table.constraints)
        for table in Base.metadata.tables.values()
    )

    assert foreign_key_count == 22
    assert Base.metadata.tables["settings"].c.user_id.unique is True
    assert Base.metadata.tables["schedules"].c.post_id.unique is True

"""Database logging hardening tests."""

from app.core.database import engine


def test_database_engine_hides_sql_parameter_values():
    """SQL echo logs must not print JWTs, passwords, or token parameters."""
    assert engine.sync_engine.hide_parameters is True

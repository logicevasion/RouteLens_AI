"""Keep application usage writes from mocked API requests in temporary databases."""

from datetime import datetime, timezone

import pytest

from app.api_usage import UsageStore


@pytest.fixture(autouse=True)
def usage_store(tmp_path, monkeypatch):
    from app.main import app

    now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
    store = UsageStore(tmp_path / "usage" / "api-usage.sqlite3", now=lambda: now)
    monkeypatch.setattr(app.state, "usage", store)
    return store

"""Test bootstrap without requiring production secrets."""
import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("BOT_USERNAME", "AccessHubTestBot")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_access_hub.sqlite3")
os.environ.setdefault("MAIN_CHANNEL_ID", "@test_channel")
os.environ.setdefault("REPORT_CHANNEL_ID", "@test_report")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("PANEL_ENCRYPTION_KEY", "")

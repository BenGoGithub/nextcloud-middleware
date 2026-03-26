"""Set fake env vars before any middleware module is imported."""
import os

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test")
os.environ.setdefault("ANTHROPIC_MODEL", "claude-sonnet-4-6")
os.environ.setdefault("CALDAV_URL", "https://nc.example.com/dav")
os.environ.setdefault("CALDAV_USERNAME", "user")
os.environ.setdefault("CALDAV_PASSWORD", "pass")
os.environ.setdefault("NEXTCLOUD_URL", "https://nc.example.com")
os.environ.setdefault("NEXTCLOUD_USERNAME", "user")
os.environ.setdefault("NEXTCLOUD_PASSWORD", "pass")

#!/usr/bin/env python3
"""
tests/test_instagram_publisher.py — Comprehensive tests for Instagram Reels publishing

Coverage targets:
  - Config validation (missing env vars)
  - Clip validation (size, format, missing file)
  - Caption validation (length, hashtags)
  - Quota checking
  - Full 4-step publish flow
  - API errors with actionable hints
  - Container polling (IN_PROGRESS → FINISHED)
  - Token refresh and exchange
"""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

import pytest

from lib import instagram_publisher as ig


class TestConfig:
    """Configuration validation."""

    def test_config_missing_token(self, monkeypatch):
        monkeypatch.delenv("IG_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("IG_USER_ID", "12345")
        with pytest.raises(ig.InstagramError, match="IG_ACCESS_TOKEN not set"):
            ig._config()

    def test_config_missing_user_id(self, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.delenv("IG_USER_ID", raising=False)
        with pytest.raises(ig.InstagramError, match="IG_USER_ID not set"):
            ig._config()

    def test_config_valid(self, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")
        token, user_id, version = ig._config()
        assert token == "token123"
        assert user_id == "12345"
        assert version == ig.GRAPH_VERSION

    def test_config_custom_graph_version(self, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")
        monkeypatch.setenv("IG_GRAPH_VERSION", "v27.0")
        _, _, version = ig._config()
        assert version == "v27.0"


class TestClipValidation:
    """Clip format and size validation."""

    def test_validate_clip_missing_file(self):
        with pytest.raises(ig.InstagramError, match="clip not found"):
            ig.validate_clip(Path("/nonexistent/video.mp4"))

    def test_validate_clip_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            path = Path(f.name)
        try:
            with pytest.raises(ig.InstagramError, match="0 bytes"):
                ig.validate_clip(path)
        finally:
            path.unlink()

    def test_validate_clip_too_large(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            # Write 301 MB
            f.write(b"x" * (301 * 1024 * 1024))
            path = Path(f.name)
        try:
            with pytest.raises(ig.InstagramError, match="Reels limit is 300 MB"):
                ig.validate_clip(path)
        finally:
            path.unlink()

    def test_validate_clip_wrong_format(self):
        with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
            f.write(b"x" * 1000)
            path = Path(f.name)
        try:
            with pytest.raises(ig.InstagramError, match="unsupported container"):
                ig.validate_clip(path)
        finally:
            path.unlink()

    def test_validate_clip_valid_mp4(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 5_000_000)  # 5 MB
            path = Path(f.name)
        try:
            ig.validate_clip(path)  # Should not raise
        finally:
            path.unlink()

    def test_validate_clip_valid_mov(self):
        with tempfile.NamedTemporaryFile(suffix=".mov", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)
        try:
            ig.validate_clip(path)
        finally:
            path.unlink()


class TestCaptionValidation:
    """Caption length and hashtag validation."""

    def test_validate_caption_within_limits(self):
        caption = "Check out this reel! #awesome"
        result = ig.validate_caption(caption)
        assert result == caption

    def test_validate_caption_too_long(self):
        long_caption = "x" * (ig.MAX_CAPTION_CHARS + 100)
        result = ig.validate_caption(long_caption)
        assert len(result) <= ig.MAX_CAPTION_CHARS
        assert result.endswith("…")

    def test_validate_caption_too_many_hashtags(self):
        caption = " ".join([f"#tag{i}" for i in range(ig.MAX_HASHTAGS + 5)])
        with pytest.raises(ig.InstagramError, match="hashtags"):
            ig.validate_caption(caption)

    def test_validate_caption_at_hashtag_limit(self):
        caption = " ".join([f"#tag{i}" for i in range(ig.MAX_HASHTAGS)])
        result = ig.validate_caption(caption)
        assert result == caption


class TestErrorParsing:
    """API error parsing and hints."""

    def test_error_from_body_valid_json(self):
        error_json = json.dumps({
            "error": {
                "code": 352,
                "error_subcode": None,
                "message": "Unsupported video format"
            }
        })
        error = ig._error_from_body(error_json, fallback="HTTP 400")
        assert error.code == 352
        assert "unsupported video format" in str(error).lower()
        assert error.permanent  # 352 is permanent

    def test_error_from_body_invalid_json(self):
        error = ig._error_from_body("{invalid json", fallback="HTTP 500")
        assert "invalid json" in str(error).lower()

    def test_error_from_body_with_hint(self):
        error_json = json.dumps({
            "error": {
                "code": 9007,
                "message": "Published before ready"
            }
        })
        error = ig._error_from_body(error_json, fallback="")
        error_str = str(error)
        # Should mention the hint from ERROR_HINTS
        assert "9007" in error_str


class TestQuotaCheck:
    """Publish quota checking."""

    @mock.patch("lib.instagram_publisher._request")
    def test_check_quota_within_limit(self, mock_request, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_request.return_value = {
            "data": [{
                "quota_usage": 5,
                "config": {"quota_total": 100}
            }]
        }
        used, total = ig.check_quota()
        assert used == 5
        assert total == 100

    @mock.patch("lib.instagram_publisher._request")
    def test_check_quota_no_data(self, mock_request, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_request.return_value = {"data": [{}]}
        used, total = ig.check_quota()
        assert used == 0
        assert total == 0


class TestCreateContainer:
    """Container creation step."""

    @mock.patch("lib.instagram_publisher._post_form")
    def test_create_container_success(self, mock_post_form, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_post_form.return_value = {"id": "container_999"}
        container_id = ig.create_container("Test caption")
        assert container_id == "container_999"

    @mock.patch("lib.instagram_publisher._post_form")
    def test_create_container_no_id(self, mock_post_form, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_post_form.return_value = {}
        with pytest.raises(ig.InstagramError, match="returned no id"):
            ig.create_container("Test caption")


class TestUploadVideo:
    """Video upload step."""

    @mock.patch("lib.instagram_publisher._request")
    def test_upload_video_success(self, mock_request, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video data")
            path = Path(f.name)

        try:
            mock_request.return_value = {}
            ig.upload_video("container_123", path)
            # Should not raise
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "rupload.facebook.com" in call_args[0][0]
        finally:
            path.unlink()


class TestContainerStatus:
    """Container status polling."""

    @mock.patch("lib.instagram_publisher._request")
    def test_container_status(self, mock_request, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_request.return_value = {
            "status_code": "FINISHED",
            "status": "some detail"
        }
        code, status = ig.container_status("container_123")
        assert code == "FINISHED"
        assert status == "some detail"


class TestWaitForContainer:
    """Container polling with timeout."""

    @mock.patch("lib.instagram_publisher.container_status")
    def test_wait_for_container_finished_immediately(self, mock_status):
        mock_status.return_value = (ig.STATUS_FINISHED, "")
        ig.wait_for_container("container_123", timeout=10, interval=1)
        # Should not raise

    @mock.patch("lib.instagram_publisher.container_status")
    def test_wait_for_container_error_state(self, mock_status):
        mock_status.return_value = (ig.STATUS_ERROR, "transcode failed")
        with pytest.raises(ig.InstagramError, match="transcode failed"):
            ig.wait_for_container("container_123", timeout=10, interval=1)

    @mock.patch("lib.instagram_publisher.container_status")
    def test_wait_for_container_expired(self, mock_status):
        mock_status.return_value = (ig.STATUS_EXPIRED, "")
        with pytest.raises(ig.InstagramError, match="expired"):
            ig.wait_for_container("container_123", timeout=10, interval=1)

    @mock.patch("lib.instagram_publisher.container_status")
    def test_wait_for_container_published(self, mock_status):
        mock_status.return_value = (ig.STATUS_PUBLISHED, "")
        ig.wait_for_container("container_123", timeout=10, interval=1)
        # Already published is treated as success

    @mock.patch("lib.instagram_publisher.container_status")
    def test_wait_for_container_timeout(self, mock_status):
        mock_status.return_value = (ig.STATUS_IN_PROGRESS, "")
        with pytest.raises(ig.InstagramError, match="giving up"):
            ig.wait_for_container("container_123", timeout=1, interval=0.1)


class TestPublishContainer:
    """Container publication step."""

    @mock.patch("lib.instagram_publisher._post_form")
    def test_publish_container_success(self, mock_post_form, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_post_form.return_value = {"id": "media_888"}
        media_id = ig.publish_container("container_123")
        assert media_id == "media_888"

    @mock.patch("lib.instagram_publisher._post_form")
    def test_publish_container_no_id(self, mock_post_form, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_post_form.return_value = {}
        with pytest.raises(ig.InstagramError, match="returned no id"):
            ig.publish_container("container_123")


class TestFullPublishFlow:
    """End-to-end publish flow with mocked API."""

    @mock.patch("lib.instagram_publisher.publish_container")
    @mock.patch("lib.instagram_publisher.wait_for_container")
    @mock.patch("lib.instagram_publisher.upload_video")
    @mock.patch("lib.instagram_publisher.create_container")
    @mock.patch("lib.instagram_publisher.check_quota")
    def test_publish_reel_success(self, mock_quota, mock_create, mock_upload,
                                   mock_wait, mock_publish, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)

        try:
            mock_quota.return_value = (10, 100)
            mock_create.return_value = "container_123"
            mock_publish.return_value = "media_999"

            result = ig.publish_reel(path, "Test Reel #awesome")

            assert result.media_id == "media_999"
            assert result.container_id == "container_123"
            assert result.quota_used == 11
            assert result.quota_total == 100

            mock_quota.assert_called_once()
            mock_create.assert_called_once()
            mock_upload.assert_called_once()
            mock_wait.assert_called_once()
            mock_publish.assert_called_once()
        finally:
            path.unlink()

    @mock.patch("lib.instagram_publisher.check_quota")
    def test_publish_reel_quota_exhausted(self, mock_quota, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("IG_USER_ID", "12345")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)

        try:
            mock_quota.return_value = (100, 100)
            with pytest.raises(ig.InstagramError, match="quota exhausted"):
                ig.publish_reel(path, "Test")
        finally:
            path.unlink()


class TestTokenRefresh:
    """Token lifecycle: refresh and exchange."""

    @mock.patch("lib.instagram_publisher._request")
    def test_refresh_token_success(self, mock_request, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "old_token")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_request.return_value = {
            "access_token": "new_token",
            "expires_in": 5184000  # 60 days
        }
        new_token, expires = ig.refresh_token()
        assert new_token == "new_token"
        assert expires == 5184000

    @mock.patch("lib.instagram_publisher._request")
    def test_refresh_token_no_token(self, mock_request, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "old_token")
        monkeypatch.setenv("IG_USER_ID", "12345")

        mock_request.return_value = {}
        with pytest.raises(ig.InstagramError, match="returned no token"):
            ig.refresh_token()

    @mock.patch("lib.instagram_publisher._request")
    def test_exchange_for_long_lived_token_success(self, mock_request, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "short_lived")
        monkeypatch.setenv("IG_USER_ID", "12345")
        monkeypatch.setenv("IG_APP_SECRET", "secret123")

        mock_request.return_value = {
            "access_token": "long_lived_token",
            "expires_in": 5184000
        }
        token, expires = ig.exchange_for_long_lived_token("short_lived")
        assert token == "long_lived_token"
        assert expires == 5184000

    def test_exchange_missing_secret(self, monkeypatch):
        monkeypatch.setenv("IG_ACCESS_TOKEN", "short_lived")
        monkeypatch.setenv("IG_USER_ID", "12345")
        monkeypatch.delenv("IG_APP_SECRET", raising=False)

        with pytest.raises(ig.InstagramError, match="IG_APP_SECRET not set"):
            ig.exchange_for_long_lived_token("short_lived")

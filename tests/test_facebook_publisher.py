#!/usr/bin/env python3
"""
tests/test_facebook_publisher.py — Comprehensive tests for Facebook Page video publishing

Coverage targets:
  - Config validation (missing env vars)
  - Clip validation (size, format, missing file)
  - Full 3-step publish flow
  - API errors with permanent flag
  - Network errors
"""

import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from lib import facebook_publisher as fb


class TestConfig:
    """Configuration validation."""

    def test_config_missing_token(self, monkeypatch):
        monkeypatch.delenv("FB_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with pytest.raises(fb.FacebookError, match="FB_ACCESS_TOKEN not set"):
            fb._config()

    def test_config_missing_page_id(self, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.delenv("FB_PAGE_ID", raising=False)
        monkeypatch.setenv("FB_APP_ID", "app789")

        with pytest.raises(fb.FacebookError, match="FB_PAGE_ID not set"):
            fb._config()

    def test_config_missing_app_id(self, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.delenv("FB_APP_ID", raising=False)

        with pytest.raises(fb.FacebookError, match="FB_APP_ID not set"):
            fb._config()

    def test_config_valid(self, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        token, page_id, app_id = fb._config()
        assert token == "token123"
        assert page_id == "123456"
        assert app_id == "app789"


class TestClipValidation:
    """Clip format and size validation."""

    def test_validate_clip_missing_file(self):
        with pytest.raises(fb.FacebookError, match="clip not found"):
            fb.validate_clip(Path("/nonexistent/video.mp4"))

    def test_validate_clip_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            path = Path(f.name)
        try:
            with pytest.raises(fb.FacebookError, match="0 bytes"):
                fb.validate_clip(path)
        finally:
            path.unlink()

    def test_validate_clip_wrong_format(self):
        with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
            f.write(b"x" * 1000)
            path = Path(f.name)
        try:
            with pytest.raises(fb.FacebookError, match="unsupported container"):
                fb.validate_clip(path)
        finally:
            path.unlink()

    def test_validate_clip_valid_mp4(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)
        try:
            size = fb.validate_clip(path)
            assert size == 5_000_000
        finally:
            path.unlink()

    def test_validate_clip_valid_mov(self):
        with tempfile.NamedTemporaryFile(suffix=".mov", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)
        try:
            size = fb.validate_clip(path)
            assert size == 5_000_000
        finally:
            path.unlink()


class TestErrorParsing:
    """API error parsing and permanent flag."""

    def test_error_from_body_valid_json(self):
        error_json = json.dumps({
            "error": {
                "code": 200,
                "error_subcode": 1234,
                "message": "Permission denied"
            }
        })
        error = fb._error_from_body(error_json, fallback="HTTP 400")
        assert error.code == 200
        assert error.subcode == 1234
        assert error.permanent  # 200 is in permanent list

    def test_error_from_body_invalid_token(self):
        error_json = json.dumps({
            "error": {
                "code": 190,
                "message": "Invalid access token"
            }
        })
        error = fb._error_from_body(error_json, fallback="")
        assert error.code == 190
        assert error.permanent  # 190 is permanent (invalid token)

    def test_error_from_body_disabled_feature(self):
        error_json = json.dumps({
            "error": {
                "code": 10,
                "message": "Feature not enabled"
            }
        })
        error = fb._error_from_body(error_json, fallback="")
        assert error.code == 10
        assert error.permanent

    def test_error_from_body_transient_error(self):
        error_json = json.dumps({
            "error": {
                "code": 17,
                "message": "Rate limited"
            }
        })
        error = fb._error_from_body(error_json, fallback="")
        assert error.code == 17
        assert not error.permanent  # Rate limit is transient

    def test_error_from_body_invalid_json(self):
        error = fb._error_from_body("{broken json", fallback="HTTP 500")
        assert "broken json" in str(error)


class TestStartUploadSession:
    """Step 1: Start upload session."""

    @mock.patch("lib.facebook_publisher._request")
    def test_start_upload_session_mp4(self, mock_request, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)

        try:
            mock_request.return_value = {"id": "session_999"}
            session_id = fb.start_upload_session(path, 5_000_000)
            assert session_id == "session_999"

            mock_request.assert_called_once()
            call_url = mock_request.call_args[0][0]
            assert "video%2Fmp4" in call_url or "video/mp4" in call_url
        finally:
            path.unlink()

    @mock.patch("lib.facebook_publisher._request")
    def test_start_upload_session_mov(self, mock_request, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with tempfile.NamedTemporaryFile(suffix=".mov", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)

        try:
            mock_request.return_value = {"id": "session_999"}
            session_id = fb.start_upload_session(path, 5_000_000)
            assert session_id == "session_999"

            call_url = mock_request.call_args[0][0]
            assert "video%2Fquicktime" in call_url or "video/quicktime" in call_url
        finally:
            path.unlink()

    @mock.patch("lib.facebook_publisher._request")
    def test_start_upload_session_no_id(self, mock_request, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 1000)
            path = Path(f.name)

        try:
            mock_request.return_value = {}
            with pytest.raises(fb.FacebookError, match="returned no id"):
                fb.start_upload_session(path, 1000)
        finally:
            path.unlink()


class TestUploadFile:
    """Step 2: Upload file bytes."""

    @mock.patch("lib.facebook_publisher._request")
    def test_upload_file_success(self, mock_request, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video data")
            path = Path(f.name)

        try:
            mock_request.return_value = {"h": "file_handle_888"}
            handle = fb.upload_file("session_999", path)
            assert handle == "file_handle_888"

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["method"] == "POST"
            assert call_kwargs["headers"]["Authorization"] == "OAuth token123"
            assert call_kwargs["headers"]["file_offset"] == "0"
        finally:
            path.unlink()

    @mock.patch("lib.facebook_publisher._request")
    def test_upload_file_no_handle(self, mock_request, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake")
            path = Path(f.name)

        try:
            mock_request.return_value = {}
            with pytest.raises(fb.FacebookError, match="returned no handle"):
                fb.upload_file("session_999", path)
        finally:
            path.unlink()


class TestPublishVideo:
    """Step 3: Publish video."""

    @mock.patch("lib.facebook_publisher._request")
    def test_publish_video_success(self, mock_request, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        mock_request.return_value = {"id": "video_777"}
        video_id = fb.publish_video("file_handle_888", "My Title", "My Description")
        assert video_id == "video_777"

        mock_request.assert_called_once()
        call_url = mock_request.call_args[0][0]
        assert "123456/videos" in call_url
        # Title is in the request body, not URL
        call_str = str(mock_request.call_args)
        assert "My Title" in call_str or "My+Title" in call_str

    @mock.patch("lib.facebook_publisher._request")
    def test_publish_video_no_id(self, mock_request, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        mock_request.return_value = {}
        with pytest.raises(fb.FacebookError, match="returned no id"):
            fb.publish_video("file_handle_888", "Title", "Desc")


class TestFullPublishFlow:
    """End-to-end publish flow."""

    @mock.patch("lib.facebook_publisher.publish_video")
    @mock.patch("lib.facebook_publisher.upload_file")
    @mock.patch("lib.facebook_publisher.start_upload_session")
    def test_publish_page_video_success(self, mock_start, mock_upload,
                                        mock_publish, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 5_000_000)
            path = Path(f.name)

        try:
            mock_start.return_value = "session_999"
            mock_upload.return_value = "file_handle_888"
            mock_publish.return_value = "video_777"

            result = fb.publish_page_video(path, "My Title", "My Description")

            assert result.video_id == "video_777"
            assert result.upload_session_id == "session_999"

            mock_start.assert_called_once()
            mock_upload.assert_called_once()
            mock_publish.assert_called_once()
        finally:
            path.unlink()

    def test_publish_page_video_missing_file(self, monkeypatch):
        monkeypatch.setenv("FB_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_APP_ID", "app789")

        with pytest.raises(fb.FacebookError, match="clip not found"):
            fb.publish_page_video(Path("/nonexistent/video.mp4"), "Title", "Desc")


class TestNetworkErrors:
    """Network and HTTP error handling."""

    @mock.patch("lib.facebook_publisher.urllib.request.urlopen")
    def test_request_network_error(self, mock_urlopen, monkeypatch):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with pytest.raises(fb.FacebookError, match="network error"):
            fb._request("https://graph.facebook.com/v25.0/test")

    @mock.patch("lib.facebook_publisher.urllib.request.urlopen")
    def test_request_http_error_with_json_body(self, mock_urlopen, monkeypatch):
        import urllib.error
        error_response = b'{"error": {"code": 190, "message": "Invalid token"}}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="test", code=401, msg="Unauthorized", hdrs={}, fp=None
        )
        mock_urlopen.side_effect.read = lambda: error_response

        with pytest.raises(fb.FacebookError) as exc_info:
            fb._request("https://graph.facebook.com/v25.0/test")

        assert exc_info.value.code == 190
        assert exc_info.value.permanent


class TestPublishResult:
    """PublishResult dataclass."""

    def test_publish_result_immutable(self):
        result = fb.PublishResult(video_id="vid_123", upload_session_id="sess_456")
        assert result.video_id == "vid_123"
        assert result.upload_session_id == "sess_456"

        with pytest.raises(AttributeError):
            result.video_id = "new_id"

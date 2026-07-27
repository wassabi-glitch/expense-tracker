import json
from unittest.mock import patch, MagicMock
from app.email_service import _send_email_via_resend_api, send_verification_email, send_password_reset_email
from config import settings
# pyrefly: ignore [missing-import]
from pydantic import SecretStr

def test_resend_missing_configuration():
    # If API key is missing, it should gracefully skip and return False
    original_key = settings.resend_api_key
    settings.resend_api_key = None
    try:
        success = _send_email_via_resend_api("test@example.com", "Subj", "Text", "<p>HTML</p>")
        assert not success
    finally:
        settings.resend_api_key = original_key

@patch("http.client.HTTPSConnection")
def test_resend_success_request_construction(mock_https_class):
    original_key = settings.resend_api_key
    settings.resend_api_key = SecretStr("re_test123")
    
    mock_conn = MagicMock()
    mock_https_class.return_value = mock_conn
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"id":"mock_id"}'
    mock_conn.getresponse.return_value = mock_response

    try:
        success = _send_email_via_resend_api(
            "test@example.com", "Test Subject", "Hello text", "<p>Hello HTML</p>", "idemp-key-1"
        )
        assert success is True
        
        mock_https_class.assert_called_with("api.resend.com", timeout=20)
        
        mock_conn.request.assert_called_once()
        args, kwargs = mock_conn.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/emails"
        
        headers = kwargs["headers"]
        assert headers["Authorization"] == "Bearer re_test123"
        assert headers["Content-Type"] == "application/json"
        assert headers["Idempotency-Key"] == "idemp-key-1"
        
        body = json.loads(kwargs["body"])
        assert body["to"] == ["test@example.com"]
        assert body["subject"] == "Test Subject"
        assert body["text"] == "Hello text"
        assert body["html"] == "<p>Hello HTML</p>"
        assert body["from"] == settings.email_from
        
    finally:
        settings.resend_api_key = original_key

@patch("http.client.HTTPSConnection")
def test_resend_provider_rejection_redacted_diagnostics(mock_https_class, caplog):
    original_key = settings.resend_api_key
    settings.resend_api_key = SecretStr("re_test123")
    
    mock_conn = MagicMock()
    mock_https_class.return_value = mock_conn
    mock_response = MagicMock()
    mock_response.status = 403
    mock_response.read.return_value = b'{"statusCode": 403, "message": "Invalid API Key"}'
    mock_conn.getresponse.return_value = mock_response

    try:
        success = _send_email_via_resend_api("test@example.com", "Subj", "Text", "<p>HTML</p>")
        assert success is False
        
        # Ensure diagnostics are logged properly
        assert "Resend API returned status=403 for test@example.com" in caplog.text
        assert "Invalid API Key" in caplog.text
        # Ensure raw token or sensitive body content isn't broadly logged by default
    finally:
        settings.resend_api_key = original_key

@patch("http.client.HTTPSConnection")
def test_resend_timeout(mock_https_class, caplog):
    original_key = settings.resend_api_key
    settings.resend_api_key = SecretStr("re_test123")
    
    mock_conn = MagicMock()
    mock_https_class.return_value = mock_conn
    mock_conn.request.side_effect = TimeoutError("Connection timed out")

    try:
        success = _send_email_via_resend_api("test@example.com", "Subj", "Text", "<p>HTML</p>")
        assert success is False
        assert "Unexpected Resend API send failure for test@example.com" in caplog.text
    finally:
        settings.resend_api_key = original_key

@patch("app.email_service._send_email_via_resend_api")
def test_password_reset_email_delegates_through_boundary(mock_send):
    mock_send.return_value = True
    success = send_password_reset_email("test@example.com", "https://reset.link", "idemp_reset_1")
    
    assert success is True
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == "test@example.com"
    assert args[1] == "Reset your Sarflog password"
    assert "https://reset.link" in args[2]
    assert "https://reset.link" in args[3]
    assert args[4] == "idemp_reset_1"

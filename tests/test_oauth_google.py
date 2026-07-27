# pyrefly: ignore [missing-import]
from unittest.mock import patch
from app import models
from config import settings

def test_google_login_native_success(client, session):
    settings.google_client_id = "test-web-id"
    settings.google_ios_client_id = "test-ios-id"
    settings.google_android_client_id = "test-android-id"

    with patch("app.routers.oauth_google.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "aud": "test-ios-id",
            "sub": "google-123",
            "email": "test@example.com",
            "email_verified": True
        }

        response = client.post("/auth/google/native", json={
            "id_token": "fake-token"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        user = session.query(models.User).filter_by(email="test@example.com").first()
        assert user is not None
        assert user.is_verified is True


def test_google_login_native_invalid_token(client):
    with patch("app.routers.oauth_google.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.side_effect = Exception("Invalid token")
        
        response = client.post("/auth/google/native", json={
            "id_token": "invalid-token"
        })

        assert response.status_code == 400
        assert response.json()["detail"] == "auth.google_id_token_invalid"


def test_google_login_native_invalid_audience(client):
    settings.google_client_id = "test-web-id"
    settings.google_ios_client_id = "test-ios-id"
    settings.google_android_client_id = "test-android-id"

    with patch("app.routers.oauth_google.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "aud": "unknown-client-id",
            "sub": "google-123"
        }

        response = client.post("/auth/google/native", json={
            "id_token": "fake-token"
        })

        assert response.status_code == 400
        assert response.json()["detail"] == "auth.google_invalid_audience"


def test_google_login_native_subject_missing(client):
    settings.google_client_id = "test-web-id"
    settings.google_ios_client_id = "test-ios-id"
    settings.google_android_client_id = "test-android-id"

    with patch("app.routers.oauth_google.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "aud": "test-ios-id",
            "sub": ""
        }

        response = client.post("/auth/google/native", json={
            "id_token": "fake-token"
        })

        assert response.status_code == 400
        assert response.json()["detail"] == "auth.google_subject_missing"

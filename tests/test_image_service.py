"""Tests for ImageService."""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.image_service import ImageService
from app.models import Customer, ImageUploadRequest


class TestImageServiceCreateUpload:
    """Tests for creating upload requests."""

    def test_create_upload_request(self, db_session):
        """Creates a token and stores the record in the database."""
        customer = Customer(phone="+15550001111", email="img@test.com")
        db_session.add(customer)
        db_session.commit()

        service = ImageService(db_session)
        request = service.create_upload_request(
            customer_id=customer.id,
            email="img@test.com",
            appliance_type="washer",
            issue_description="leaking",
        )

        assert request.id is not None
        assert request.upload_token is not None
        assert len(request.upload_token) > 20
        assert request.email_sent_to == "img@test.com"
        assert request.appliance_type == "washer"
        assert request.is_used is False

    def test_get_upload_url(self, db_session):
        """Upload URL includes the base URL and token."""
        service = ImageService(db_session)
        url = service.get_upload_url("my_token_123")
        assert "upload/my_token_123" in url


class TestImageServiceValidation:
    """Tests for token validation."""

    def _create_request(self, db_session, **overrides):
        """Helper to create a customer and upload request."""
        customer = Customer(phone="+15550009999")
        db_session.add(customer)
        db_session.commit()

        defaults = {
            "customer_id": customer.id,
            "upload_token": "valid_token_abc",
            "email_sent_to": "v@test.com",
            "email_sent_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "is_used": False,
        }
        defaults.update(overrides)
        req = ImageUploadRequest(**defaults)
        db_session.add(req)
        db_session.commit()
        return req

    def test_validate_upload_token_valid(self, db_session):
        """Valid token returns (True, None)."""
        self._create_request(db_session)
        service = ImageService(db_session)
        is_valid, error = service.validate_upload_token("valid_token_abc")
        assert is_valid is True
        assert error is None

    def test_validate_upload_token_invalid(self, db_session):
        """Nonexistent token returns (False, 'Invalid upload link')."""
        service = ImageService(db_session)
        is_valid, error = service.validate_upload_token("does_not_exist")
        assert is_valid is False
        assert "Invalid" in error

    def test_validate_upload_token_expired(self, db_session):
        """Expired token returns (False, 'expired')."""
        self._create_request(
            db_session,
            upload_token="expired_tok",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        service = ImageService(db_session)
        is_valid, error = service.validate_upload_token("expired_tok")
        assert is_valid is False
        assert "expired" in error.lower()

    def test_validate_upload_token_used(self, db_session):
        """Already-used token returns (False, 'already been used')."""
        self._create_request(
            db_session,
            upload_token="used_tok",
            is_used=True,
        )
        service = ImageService(db_session)
        is_valid, error = service.validate_upload_token("used_tok")
        assert is_valid is False
        assert "used" in error.lower()


class TestImageServiceSaveAndAnalyze:
    """Tests for saving uploaded images."""

    def _seed(self, db_session):
        customer = Customer(phone="+15550005555")
        db_session.add(customer)
        db_session.commit()

        req = ImageUploadRequest(
            customer_id=customer.id,
            upload_token="save_tok",
            email_sent_to="s@test.com",
            email_sent_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False,
        )
        db_session.add(req)
        db_session.commit()
        return req

    @pytest.mark.asyncio
    async def test_save_uploaded_image(self, db_session, tmp_path):
        """Saves file to disk and marks token as used."""
        self._seed(db_session)
        service = ImageService(db_session)

        with patch("app.services.image_service.UPLOAD_DIR", tmp_path):
            success, result = await service.save_uploaded_image(
                token="save_tok",
                image_data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
                filename="photo.png",
            )

        assert success is True
        assert result is not None

        req = service.get_upload_request_by_token("save_tok")
        assert req.is_used is True

    @pytest.mark.asyncio
    async def test_save_uploaded_image_invalid_token(self, db_session):
        """Saving with an invalid token fails gracefully."""
        service = ImageService(db_session)
        success, error = await service.save_uploaded_image(
            token="bad_token",
            image_data=b"data",
            filename="photo.jpg",
        )
        assert success is False
        assert "Invalid" in error

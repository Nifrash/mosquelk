from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import OTPPurpose
from .otp import (
    OTPVerificationError,
    consume_otp_challenge,
    start_otp_challenge,
    verify_otp_code,
)


@override_settings(
    OTP_SMS_BACKEND="support_requests.sms_backends.ConsoleSMSBackend",
    OTP_EXPIRY_SECONDS=300,
    OTP_MAX_ATTEMPTS=5,
    OTP_MAX_SENDS_PER_HOUR=5,
)
class SMSOTPChallengeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mosqueadmin",
            email="mosqueadmin@example.com",
            password="StrongPass123!",
            phone_number="+94770000000",
            is_active=False,
        )

    @patch("accounts.otp._generate_code", return_value="123456")
    def test_otp_is_hashed_verified_and_consumed(self, _mock_code):
        challenge, delivered, _details = start_otp_challenge(
            user=self.user,
            phone_number=self.user.phone_number,
            purpose=OTPPurpose.ACCOUNT_REGISTRATION,
            session_key="test-session",
            target_reference=str(self.user.pk),
        )

        self.assertTrue(delivered)
        self.assertNotEqual(challenge.code_hash, "123456")

        verify_otp_code(challenge, "123456")
        challenge.refresh_from_db()
        self.assertIsNotNone(challenge.verified_at)

        consume_otp_challenge(challenge)
        challenge.refresh_from_db()
        self.assertIsNotNone(challenge.consumed_at)

    @patch("accounts.otp._generate_code", return_value="123456")
    def test_wrong_otp_increments_attempt_count(self, _mock_code):
        challenge, _delivered, _details = start_otp_challenge(
            user=self.user,
            phone_number=self.user.phone_number,
            purpose=OTPPurpose.ACCOUNT_REGISTRATION,
            session_key="test-session",
            target_reference=str(self.user.pk),
        )

        with self.assertRaises(OTPVerificationError):
            verify_otp_code(challenge, "000000")

        challenge.refresh_from_db()
        self.assertEqual(challenge.attempt_count, 1)

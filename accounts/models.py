from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    MOSQUE_ADMIN = "MOSQUE_ADMIN", _("Mosque Admin")
    MOSQUE_STAFF = "MOSQUE_STAFF", _("Mosque Staff")
    DISTRICT_OFFICER = "DISTRICT_OFFICER", _("District Officer")
    SUPPORT_OFFICER = "SUPPORT_OFFICER", _("Support Officer")
    PLATFORM_ADMIN = "PLATFORM_ADMIN", _("Platform Admin")
    SUPER_ADMIN = "SUPER_ADMIN", _("Super Admin")


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.MOSQUE_STAFF,
        db_index=True,
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    preferred_language = models.CharField(
        max_length=5,
        choices=[("en", "English"), ("ta", "தமிழ்"), ("ar", "العربية")],
        default="en",
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["username"]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.is_superuser:
            self.role = UserRole.SUPER_ADMIN
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def role_label(self):
        return self.get_role_display()

    def __str__(self):
        return self.get_full_name() or self.username

class OTPPurpose(models.TextChoices):
    ACCOUNT_REGISTRATION = "ACCOUNT_REGISTRATION", _("Account Registration")
    MOSQUE_SUBMISSION = "MOSQUE_SUBMISSION", _("Mosque Registration Submission")
    SUPPORT_SUBMISSION = "SUPPORT_SUBMISSION", _("Support Request Submission")


class SMSOTPChallenge(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="sms_otp_challenges",
        null=True,
        blank=True,
    )
    phone_number = models.CharField(max_length=30, db_index=True)
    purpose = models.CharField(max_length=40, choices=OTPPurpose.choices, db_index=True)
    target_reference = models.CharField(max_length=160, blank=True, db_index=True)
    code_hash = models.CharField(max_length=255)
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    send_count = models.PositiveSmallIntegerField(default=1)
    last_sent_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=160, blank=True)
    last_delivery_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["phone_number", "purpose", "created_at"],
                name="acct_otp_phone_purpose_idx",
            ),
            models.Index(
                fields=["user", "purpose", "consumed_at"],
                name="acct_otp_user_purpose_idx",
            ),
        ]
        verbose_name = _("SMS OTP challenge")
        verbose_name_plural = _("SMS OTP challenges")

    @property
    def is_verified(self):
        return self.verified_at is not None

    @property
    def is_consumed(self):
        return self.consumed_at is not None

    def __str__(self):
        return f"{self.get_purpose_display()} - {self.phone_number}"


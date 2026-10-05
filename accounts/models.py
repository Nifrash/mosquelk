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

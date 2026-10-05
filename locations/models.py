from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _


class LocalizedNameMixin:
    def get_localized_name(self, language=None):
        language = (language or get_language() or "en").split("-")[0]
        if language in {"en", "ta", "ar"}:
            value = getattr(self, f"name_{language}", "")
            if value:
                return value
        return self.name_en

    @property
    def localized_name(self):
        return self.get_localized_name()


class Province(LocalizedNameMixin, models.Model):
    code = models.CharField(max_length=10, unique=True)
    name_en = models.CharField(max_length=120)
    name_ta = models.CharField(max_length=120, blank=True)
    name_ar = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        verbose_name = _("province")
        verbose_name_plural = _("provinces")

    def __str__(self):
        return self.name_en


class District(LocalizedNameMixin, models.Model):
    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name="districts",
    )
    code = models.CharField(max_length=10, unique=True)
    name_en = models.CharField(max_length=120)
    name_ta = models.CharField(max_length=120, blank=True)
    name_ar = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["province", "name_en"],
                name="unique_district_name_per_province",
            )
        ]
        verbose_name = _("district")
        verbose_name_plural = _("districts")

    def __str__(self):
        return f"{self.name_en} - {self.province.name_en}"


class DivisionalSecretariat(LocalizedNameMixin, models.Model):
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="divisional_secretariats",
    )
    code = models.CharField(max_length=30, unique=True)
    name_en = models.CharField(max_length=160)
    name_ta = models.CharField(max_length=160, blank=True)
    name_ar = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["district", "name_en"],
                name="unique_ds_name_per_district",
            )
        ]
        verbose_name = _("divisional secretariat")
        verbose_name_plural = _("divisional secretariats")

    def __str__(self):
        return f"{self.name_en} - {self.district.name_en}"


class GNDivision(LocalizedNameMixin, models.Model):
    divisional_secretariat = models.ForeignKey(
        DivisionalSecretariat,
        on_delete=models.PROTECT,
        related_name="gn_divisions",
    )
    code = models.CharField(max_length=40, unique=True)
    name_en = models.CharField(max_length=180)
    name_ta = models.CharField(max_length=180, blank=True)
    name_ar = models.CharField(max_length=180, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["divisional_secretariat", "name_en"],
                name="unique_gn_name_per_ds",
            )
        ]
        verbose_name = _("GN division")
        verbose_name_plural = _("GN divisions")

    def __str__(self):
        return f"{self.name_en} - {self.divisional_secretariat.name_en}"


class DistrictOfficerAssignment(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="district_assignment",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="officer_assignments",
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["district__name_en", "user__username"]
        verbose_name = _("district officer assignment")
        verbose_name_plural = _("district officer assignments")

    def clean(self):
        super().clean()
        if self.user_id and not self.user.is_superuser:
            if self.user.role != "DISTRICT_OFFICER":
                raise ValidationError(
                    {"user": _("Only users with the District Officer role can be assigned to a district.")}
                )

    def __str__(self):
        return f"{self.user} → {self.district.name_en}"

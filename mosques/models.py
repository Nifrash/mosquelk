from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _

from locations.models import District, DivisionalSecretariat, GNDivision, Province


class MosqueStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    SUBMITTED = "SUBMITTED", _("Pending Platform Approval")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class MosqueCategory(models.TextChoices):
    JUMMA = "JUMMA", _("Jumma Mosque")
    MASJID = "MASJID", _("Mosque / Masjid")
    MUSALLA = "MUSALLA", _("Musalla / Prayer Hall")
    OTHER = "OTHER", _("Other")


class MosqueMembershipRole(models.TextChoices):
    ADMIN = "ADMIN", _("Mosque Admin")
    STAFF = "STAFF", _("Mosque Staff")


class CommitteeDesignation(models.TextChoices):
    PRESIDENT = "PRESIDENT", _("President / Chairman")
    SECRETARY = "SECRETARY", _("Secretary")
    TREASURER = "TREASURER", _("Treasurer")
    TRUSTEE = "TRUSTEE", _("Trustee")
    IMAM = "IMAM", _("Imam")
    MUEZZIN = "MUEZZIN", _("Muezzin")
    MEMBER = "MEMBER", _("Committee Member")
    OTHER = "OTHER", _("Other")


class DocumentType(models.TextChoices):
    REGISTRATION = "REGISTRATION", _("Existing Registration Certificate")
    COMMITTEE = "COMMITTEE", _("Committee Authorization / Letter")
    LAND = "LAND", _("Land / Property Document")
    BUILDING = "BUILDING", _("Building / Construction Document")
    PHOTO = "PHOTO", _("Mosque Photograph")
    OTHER = "OTHER", _("Other Supporting Document")


class LocalizedMosqueMixin:
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


class Mosque(LocalizedMosqueMixin, models.Model):
    mosque_id = models.CharField(
        max_length=24,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    name_en = models.CharField(max_length=220, verbose_name=_("Mosque name (English)"))
    name_ta = models.CharField(max_length=220, blank=True, verbose_name=_("Mosque name (Tamil)"))
    name_ar = models.CharField(max_length=220, blank=True, verbose_name=_("Mosque name (Arabic)"))
    category = models.CharField(
        max_length=20,
        choices=MosqueCategory.choices,
        default=MosqueCategory.MASJID,
    )
    established_year = models.PositiveSmallIntegerField(null=True, blank=True)
    existing_registration_number = models.CharField(max_length=100, blank=True)

    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name="mosques",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="mosques",
    )
    divisional_secretariat = models.ForeignKey(
        DivisionalSecretariat,
        on_delete=models.PROTECT,
        related_name="mosques",
        null=True,
        blank=True,
    )
    gn_division = models.ForeignKey(
        GNDivision,
        on_delete=models.PROTECT,
        related_name="mosques",
        null=True,
        blank=True,
    )

    address_line1 = models.CharField(max_length=220)
    address_line2 = models.CharField(max_length=220, blank=True)
    city_or_town = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20, blank=True)

    official_phone = models.CharField(max_length=30)
    alternate_phone = models.CharField(max_length=30, blank=True)
    official_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    description_en = models.TextField(blank=True, verbose_name=_("Description (English)"))
    description_ta = models.TextField(blank=True, verbose_name=_("Description (Tamil)"))
    description_ar = models.TextField(blank=True, verbose_name=_("Description (Arabic)"))

    status = models.CharField(
        max_length=25,
        choices=MosqueStatus.choices,
        default=MosqueStatus.DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_mosque_applications",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_mosque_applications",
        null=True,
        blank=True,
    )
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "district"], name="mosque_status_district_idx"),
            models.Index(fields=["name_en"], name="mosque_name_en_idx"),
        ]
        verbose_name = _("mosque")
        verbose_name_plural = _("mosques")

    def __str__(self):
        return f"{self.mosque_id or 'New'} - {self.name_en}"

    @property
    def is_editable(self):
        return self.status == MosqueStatus.DRAFT

    @property
    def is_public(self):
        return self.status == MosqueStatus.APPROVED

    def clean(self):
        super().clean()

        if self.district_id and self.province_id:
            if self.district.province_id != self.province_id:
                raise ValidationError(
                    {"district": _("The selected district does not belong to the selected province.")}
                )

        if self.divisional_secretariat_id:
            if not self.district_id or self.divisional_secretariat.district_id != self.district_id:
                raise ValidationError(
                    {
                        "divisional_secretariat": _(
                            "The selected Divisional Secretariat does not belong to the selected district."
                        )
                    }
                )

        if self.gn_division_id:
            if (
                not self.divisional_secretariat_id
                or self.gn_division.divisional_secretariat_id != self.divisional_secretariat_id
            ):
                raise ValidationError(
                    {
                        "gn_division": _(
                            "The selected GN Division does not belong to the selected Divisional Secretariat."
                        )
                    }
                )

        if self.established_year:
            current_year = timezone.localdate().year
            if self.established_year < 1200 or self.established_year > current_year:
                raise ValidationError(
                    {"established_year": _("Enter a valid mosque establishment year.")}
                )

    def save(self, *args, **kwargs):
        is_new_without_id = self.pk is None and not self.mosque_id
        super().save(*args, **kwargs)
        if is_new_without_id:
            self.mosque_id = f"SL-MOS-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(mosque_id=self.mosque_id)


class MosqueOperationalProfile(models.Model):
    mosque = models.OneToOneField(
        Mosque,
        on_delete=models.CASCADE,
        related_name="operational_profile",
    )
    public_phone = models.CharField(max_length=30, blank=True)
    whatsapp_number = models.CharField(max_length=30, blank=True)
    public_email = models.EmailField(blank=True)

    imam_name = models.CharField(max_length=180, blank=True)
    muezzin_name = models.CharField(max_length=180, blank=True)
    jummah_prayer_time = models.TimeField(null=True, blank=True)

    capacity_men = models.PositiveIntegerField(null=True, blank=True)
    capacity_women = models.PositiveIntegerField(null=True, blank=True)

    has_womens_prayer_area = models.BooleanField(default=False)
    has_parking = models.BooleanField(default=False)
    wheelchair_accessible = models.BooleanField(default=False)
    has_wudu_facilities = models.BooleanField(default=True)
    has_madrasa = models.BooleanField(default=False)

    public_summary_en = models.TextField(blank=True, verbose_name=_("Public summary (English)"))
    public_summary_ta = models.TextField(blank=True, verbose_name=_("Public summary (Tamil)"))
    public_summary_ar = models.TextField(blank=True, verbose_name=_("Public summary (Arabic)"))

    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_mosque_operational_profiles",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("mosque operational profile")
        verbose_name_plural = _("mosque operational profiles")

    def __str__(self):
        return f"Operational profile - {self.mosque}"

    def get_localized_summary(self, language=None):
        language = (language or get_language() or "en").split("-")[0]
        if language in {"en", "ta", "ar"}:
            value = getattr(self, f"public_summary_{language}", "")
            if value:
                return value
        return self.public_summary_en

    @property
    def localized_summary(self):
        return self.get_localized_summary()

    @property
    def profile_completion_percent(self):
        checks = [
            self.public_phone or self.mosque.official_phone,
            self.public_email or self.mosque.official_email,
            self.imam_name,
            self.jummah_prayer_time,
            self.public_summary_en,
            self.capacity_men,
        ]
        completed = sum(bool(item) for item in checks)
        return round((completed / len(checks)) * 100)


class MosqueMembership(models.Model):
    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mosque_memberships",
    )
    membership_role = models.CharField(
        max_length=10,
        choices=MosqueMembershipRole.choices,
        default=MosqueMembershipRole.STAFF,
    )
    is_active = models.BooleanField(default=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="added_mosque_memberships",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["mosque__name_en", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["mosque", "user"],
                name="unique_user_membership_per_mosque",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.mosque.name_en} ({self.get_membership_role_display()})"


class MosqueCommitteeMember(models.Model):
    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="committee_members",
    )
    full_name = models.CharField(max_length=180)
    designation = models.CharField(
        max_length=20,
        choices=CommitteeDesignation.choices,
        default=CommitteeDesignation.MEMBER,
    )
    phone_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_primary_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["designation", "full_name"]

    def __str__(self):
        return f"{self.full_name} - {self.get_designation_display()}"



def mosque_document_upload_to(instance, filename):
    safe_name = Path(filename).name
    mosque_ref = instance.mosque.mosque_id or f"mosque-{instance.mosque_id}"
    return f"mosques/{mosque_ref}/documents/{safe_name}"


class MosqueDocument(models.Model):
    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    title = models.CharField(max_length=180)
    file = models.FileField(upload_to=mosque_document_upload_to)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_mosque_documents",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MosqueReviewHistory(models.Model):
    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="review_history",
    )
    from_status = models.CharField(max_length=25, choices=MosqueStatus.choices)
    to_status = models.CharField(max_length=25, choices=MosqueStatus.choices)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="mosque_review_actions",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("mosque review history")
        verbose_name_plural = _("mosque review history")

    def __str__(self):
        return f"{self.mosque.mosque_id}: {self.from_status} → {self.to_status}"

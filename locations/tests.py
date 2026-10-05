from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from accounts.models import UserRole
from .models import (
    District,
    DistrictOfficerAssignment,
    DivisionalSecretariat,
    GNDivision,
    Province,
)


class LocationModelTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(
            code="EP",
            name_en="Eastern Province",
            name_ta="கிழக்கு மாகாணம்",
        )
        self.district = District.objects.create(
            province=self.province,
            code="AMP",
            name_en="Ampara",
        )
        self.ds = DivisionalSecretariat.objects.create(
            district=self.district,
            code="DS001",
            name_en="Example DS",
        )
        self.gn = GNDivision.objects.create(
            divisional_secretariat=self.ds,
            code="GN001",
            name_en="Example GN",
        )

    def test_hierarchy(self):
        self.assertEqual(self.district.province, self.province)
        self.assertEqual(self.ds.district, self.district)
        self.assertEqual(self.gn.divisional_secretariat, self.ds)

    def test_localized_name_uses_translation_and_fallback(self):
        with translation.override("ta"):
            self.assertEqual(
                self.province.get_localized_name(),
                "கிழக்கு மாகாணம்",
            )
            self.assertEqual(
                self.district.get_localized_name(),
                "Ampara",
            )

    def test_dependent_api_filters_by_parent(self):
        response = self.client.get(
            reverse("locations:api_districts"),
            {"province": self.province.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["text"], "Ampara")

        response = self.client.get(
            reverse("locations:api_ds_divisions"),
            {"district": self.district.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["text"], "Example DS")

        response = self.client.get(
            reverse("locations:api_gn_divisions"),
            {"ds": self.ds.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["text"], "Example GN")


class LocationAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.platform_admin = User.objects.create_user(
            username="platform",
            email="platform@example.com",
            password="StrongPass123!",
            role=UserRole.PLATFORM_ADMIN,
        )
        self.mosque_admin = User.objects.create_user(
            username="mosque",
            email="mosque@example.com",
            password="StrongPass123!",
            role=UserRole.MOSQUE_ADMIN,
        )

    def test_platform_admin_can_open_location_management(self):
        self.client.force_login(self.platform_admin)
        response = self.client.get(reverse("locations:management"))
        self.assertEqual(response.status_code, 200)

    def test_mosque_admin_cannot_open_location_management(self):
        self.client.force_login(self.mosque_admin)
        response = self.client.get(reverse("locations:management"))
        self.assertEqual(response.status_code, 403)


class DistrictOfficerAssignmentTests(TestCase):
    def test_district_officer_assignment(self):
        call_command("seed_sri_lanka_locations", verbosity=0)

        User = get_user_model()
        officer = User.objects.create_user(
            username="district1",
            email="district1@example.com",
            password="StrongPass123!",
            role=UserRole.DISTRICT_OFFICER,
        )

        district = District.objects.get(code="AMP")
        assignment = DistrictOfficerAssignment.objects.create(
            user=officer,
            district=district,
        )

        self.assertEqual(assignment.user, officer)
        self.assertEqual(assignment.district.code, "AMP")


class SeedCommandTests(TestCase):
    def test_seed_creates_nine_provinces_and_twenty_five_districts(self):
        call_command("seed_sri_lanka_locations", verbosity=0)

        self.assertEqual(Province.objects.count(), 9)
        self.assertEqual(District.objects.count(), 25)

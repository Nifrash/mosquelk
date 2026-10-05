from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserRole
from locations.models import District, Province
from .models import (
    Mosque,
    MosqueCommitteeMember,
    MosqueMembership,
    MosqueOperationalProfile,
    MosqueStatus,
)


class MosquePhase4Base(TestCase):
    def setUp(self):
        User = get_user_model()

        self.province = Province.objects.create(
            code="EP",
            name_en="Eastern Province",
        )
        self.ampara = District.objects.create(
            province=self.province,
            code="AMP",
            name_en="Ampara",
        )
        self.batticaloa = District.objects.create(
            province=self.province,
            code="BAT",
            name_en="Batticaloa",
        )

        self.mosque_admin = User.objects.create_user(
            username="mosqueadmin",
            email="mosqueadmin@example.com",
            password="StrongPass123!",
            role=UserRole.MOSQUE_ADMIN,
        )
        self.district_officer = User.objects.create_user(
            username="district1",
            email="district1@example.com",
            password="StrongPass123!",
            role=UserRole.DISTRICT_OFFICER,
        )
        self.platform_admin = User.objects.create_user(
            username="platform1",
            email="platform1@example.com",
            password="StrongPass123!",
            role=UserRole.PLATFORM_ADMIN,
        )


    def make_mosque(self, *, district=None, status=MosqueStatus.DRAFT, name="Test Mosque"):
        district = district or self.ampara
        mosque = Mosque.objects.create(
            name_en=name,
            category="MASJID",
            province=district.province,
            district=district,
            address_line1="Main Street",
            city_or_town="Akkaraipattu",
            official_phone="+94770000000",
            official_email="mosque@example.com",
            created_by=self.mosque_admin,
            status=status,
        )
        MosqueMembership.objects.create(
            mosque=mosque,
            user=self.mosque_admin,
            membership_role="ADMIN",
            added_by=self.mosque_admin,
        )
        return mosque


class MosqueModelTests(MosquePhase4Base):
    def test_unique_mosque_id_is_generated(self):
        first = self.make_mosque(name="First Mosque")
        second = self.make_mosque(name="Second Mosque")

        self.assertTrue(first.mosque_id.startswith("SL-MOS-"))
        self.assertTrue(second.mosque_id.startswith("SL-MOS-"))
        self.assertNotEqual(first.mosque_id, second.mosque_id)

    def test_location_hierarchy_validation(self):
        western = Province.objects.create(code="WP", name_en="Western Province")
        invalid = Mosque(
            name_en="Invalid Mosque",
            province=western,
            district=self.ampara,
            address_line1="Test",
            city_or_town="Test",
            official_phone="123",
            created_by=self.mosque_admin,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()


class MosqueRegistrationViewTests(MosquePhase4Base):
    def test_mosque_admin_can_create_draft(self):
        self.client.force_login(self.mosque_admin)
        response = self.client.post(
            reverse("mosques:create"),
            {
                "name_en": "New Central Mosque",
                "name_ta": "",
                "name_ar": "",
                "category": "MASJID",
                "established_year": "",
                "existing_registration_number": "",
                "province": self.province.pk,
                "district": self.ampara.pk,
                "divisional_secretariat": "",
                "gn_division": "",
                "address_line1": "1 Main Road",
                "address_line2": "",
                "city_or_town": "Akkaraipattu",
                "postal_code": "",
                "official_phone": "+94771111111",
                "alternate_phone": "",
                "official_email": "newmosque@example.com",
                "website": "",
                "description_en": "",
                "description_ta": "",
                "description_ar": "",
            },
        )

        mosque = Mosque.objects.get(name_en="New Central Mosque")
        self.assertRedirects(
            response,
            reverse("mosques:detail", args=[mosque.mosque_id]),
        )
        self.assertEqual(mosque.status, MosqueStatus.DRAFT)
        self.assertTrue(
            MosqueMembership.objects.filter(
                mosque=mosque,
                user=self.mosque_admin,
                membership_role="ADMIN",
            ).exists()
        )

    def test_submit_changes_status_to_submitted(self):
        mosque = self.make_mosque()
        self.client.force_login(self.mosque_admin)

        response = self.client.post(
            reverse("mosques:submit", args=[mosque.mosque_id])
        )

        self.assertRedirects(
            response,
            reverse("mosques:detail", args=[mosque.mosque_id]),
        )
        mosque.refresh_from_db()
        self.assertEqual(mosque.status, MosqueStatus.SUBMITTED)
        self.assertIsNotNone(mosque.submitted_at)
        self.assertEqual(mosque.review_history.count(), 0)


class MosqueReviewTests(MosquePhase4Base):
    def test_district_officer_cannot_access_mosque_approval_queue(self):
        self.make_mosque(
            district=self.ampara,
            status=MosqueStatus.SUBMITTED,
            name="Ampara Mosque",
        )

        self.client.force_login(self.district_officer)
        response = self.client.get(reverse("mosques:review_queue"))

        self.assertEqual(response.status_code, 403)

    def test_platform_admin_can_approve_registration(self):
        mosque = self.make_mosque(status=MosqueStatus.SUBMITTED)
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse("mosques:review_action", args=[mosque.mosque_id]),
            {
                "action": MosqueStatus.APPROVED,
                "notes": "Verified and approved.",
            },
        )

        self.assertRedirects(
            response,
            reverse("mosques:review_detail", args=[mosque.mosque_id]),
        )
        mosque.refresh_from_db()
        self.assertEqual(mosque.status, MosqueStatus.APPROVED)
        self.assertEqual(mosque.reviewed_by, self.platform_admin)
        self.assertEqual(mosque.review_history.count(), 1)

    def test_rejection_requires_notes(self):
        mosque = self.make_mosque(status=MosqueStatus.SUBMITTED)
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse("mosques:review_action", args=[mosque.mosque_id]),
            {
                "action": MosqueStatus.REJECTED,
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        mosque.refresh_from_db()
        self.assertEqual(mosque.status, MosqueStatus.SUBMITTED)


class MosqueDirectoryTests(MosquePhase4Base):
    def test_directory_only_shows_approved_mosques(self):
        approved = self.make_mosque(
            status=MosqueStatus.APPROVED,
            name="Approved Mosque",
        )
        draft = self.make_mosque(
            status=MosqueStatus.DRAFT,
            name="Draft Mosque",
        )

        response = self.client.get(reverse("mosques:directory"))

        self.assertContains(response, approved.name_en)
        self.assertNotContains(response, draft.name_en)

    def test_public_detail_rejects_non_approved_mosque(self):
        mosque = self.make_mosque(status=MosqueStatus.DRAFT)
        response = self.client.get(
            reverse("mosques:public_detail", args=[mosque.mosque_id])
        )
        self.assertEqual(response.status_code, 404)


class MosquePhase5PortalTests(MosquePhase4Base):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="mosquestaff",
            email="staff@example.com",
            password="StrongPass123!",
            role=UserRole.MOSQUE_STAFF,
        )
        self.approved = self.make_mosque(
            status=MosqueStatus.APPROVED,
            name="Approved Portal Mosque",
        )
        MosqueMembership.objects.create(
            mosque=self.approved,
            user=self.staff,
            membership_role="STAFF",
            added_by=self.mosque_admin,
        )

    def test_approved_mosque_admin_can_open_portal(self):
        self.client.force_login(self.mosque_admin)
        response = self.client.get(
            reverse("mosques:portal", args=[self.approved.mosque_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved Mosque Portal")
        self.assertTrue(
            MosqueOperationalProfile.objects.filter(mosque=self.approved).exists()
        )

    def test_staff_can_view_portal_but_cannot_edit_profile(self):
        self.client.force_login(self.staff)
        portal_response = self.client.get(
            reverse("mosques:portal", args=[self.approved.mosque_id])
        )
        self.assertEqual(portal_response.status_code, 200)

        edit_response = self.client.get(
            reverse(
                "mosques:operational_profile_edit",
                args=[self.approved.mosque_id],
            )
        )
        self.assertEqual(edit_response.status_code, 403)

    def test_admin_can_update_operational_profile_without_new_approval(self):
        self.client.force_login(self.mosque_admin)
        response = self.client.post(
            reverse(
                "mosques:operational_profile_edit",
                args=[self.approved.mosque_id],
            ),
            {
                "public_phone": "+94771234567",
                "whatsapp_number": "+94771234567",
                "public_email": "public@example.com",
                "imam_name": "Imam Abdul Rahman",
                "muezzin_name": "Muezzin Ahmed",
                "jummah_prayer_time": "12:45",
                "capacity_men": "800",
                "capacity_women": "150",
                "has_womens_prayer_area": "on",
                "has_parking": "on",
                "wheelchair_accessible": "on",
                "has_wudu_facilities": "on",
                "has_madrasa": "on",
                "public_summary_en": "Community mosque serving local residents.",
                "public_summary_ta": "",
                "public_summary_ar": "",
                "facebook_url": "",
                "youtube_url": "",
            },
        )
        self.assertRedirects(
            response,
            reverse("mosques:portal", args=[self.approved.mosque_id]),
        )
        self.approved.refresh_from_db()
        profile = self.approved.operational_profile
        self.assertEqual(profile.imam_name, "Imam Abdul Rahman")
        self.assertEqual(self.approved.status, MosqueStatus.APPROVED)

    def test_approved_mosque_admin_can_manage_committee(self):
        self.client.force_login(self.mosque_admin)
        response = self.client.post(
            reverse("mosques:committee_add", args=[self.approved.mosque_id]),
            {
                "full_name": "Mohamed Secretary",
                "designation": "SECRETARY",
                "phone_number": "0771234567",
                "email": "",
                "is_primary_contact": "on",
            },
        )
        self.assertRedirects(
            response,
            reverse("mosques:portal", args=[self.approved.mosque_id]),
        )
        self.assertTrue(
            MosqueCommitteeMember.objects.filter(
                mosque=self.approved,
                full_name="Mohamed Secretary",
            ).exists()
        )

    def test_draft_mosque_cannot_open_operational_portal(self):
        draft = self.make_mosque(status=MosqueStatus.DRAFT, name="Draft Portal Mosque")
        self.client.force_login(self.mosque_admin)
        response = self.client.get(
            reverse("mosques:portal", args=[draft.mosque_id])
        )
        self.assertRedirects(
            response,
            reverse("mosques:detail", args=[draft.mosque_id]),
        )

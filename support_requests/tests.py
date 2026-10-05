from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserRole
from locations.models import District, Province
from mosques.models import (
    Mosque,
    MosqueMembership,
    MosqueMembershipRole,
    MosqueStatus,
)

from .models import (
    MosqueSupportRequest,
    NotificationChannel,
    NotificationDeliveryStatus,
    SupportNotification,
    SupportNotificationType,
    SupportRequestHistory,
    SupportRequestStatus,
)


class SupportRequestFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.mosque_admin = User.objects.create_user(
            username="mosqueadmin",
            email="mosqueadmin@example.com",
            password="StrongPass123!",
            role=UserRole.MOSQUE_ADMIN,
        )
        self.mosque_staff = User.objects.create_user(
            username="mosquestaff",
            email="mosquestaff@example.com",
            password="StrongPass123!",
            role=UserRole.MOSQUE_STAFF,
        )
        self.support_officer = User.objects.create_user(
            username="support",
            email="support@example.com",
            password="StrongPass123!",
            role=UserRole.SUPPORT_OFFICER,
        )
        self.platform_admin = User.objects.create_user(
            username="platform",
            email="platform@example.com",
            password="StrongPass123!",
            role=UserRole.PLATFORM_ADMIN,
        )
        self.mosque_admin.phone_number = "0771234567"
        self.mosque_admin.save(update_fields=["phone_number"])

        self.province = Province.objects.create(
            code="EP",
            name_en="Eastern Province",
        )
        self.district = District.objects.create(
            province=self.province,
            code="AMP",
            name_en="Ampara",
        )
        self.mosque = Mosque.objects.create(
            name_en="Approved Test Mosque",
            category="JUMMA",
            province=self.province,
            district=self.district,
            address_line1="Main Street",
            city_or_town="Akkaraipattu",
            official_phone="0771234567",
            status=MosqueStatus.APPROVED,
            created_by=self.mosque_admin,
        )

        MosqueMembership.objects.create(
            mosque=self.mosque,
            user=self.mosque_admin,
            membership_role=MosqueMembershipRole.ADMIN,
            is_active=True,
            added_by=self.mosque_admin,
        )
        MosqueMembership.objects.create(
            mosque=self.mosque,
            user=self.mosque_staff,
            membership_role=MosqueMembershipRole.STAFF,
            is_active=True,
            added_by=self.mosque_admin,
        )

        self.support_request = MosqueSupportRequest.objects.create(
            mosque=self.mosque,
            category="CONSTRUCTION",
            priority="HIGH",
            title="Roof repair",
            issue_description="Roof is leaking.",
            requested_support="Repair materials and labour.",
            requested_amount="250000.00",
            contact_person="Secretary",
            contact_phone="0771111111",
            created_by=self.mosque_admin,
        )

    def test_request_number_is_generated(self):
        self.assertTrue(
            self.support_request.request_no.startswith("SUP-")
        )

    def test_mosque_admin_can_view_and_edit_draft(self):
        self.client.force_login(self.mosque_admin)

        response = self.client.get(
            reverse(
                "support_requests:detail",
                kwargs={"request_no": self.support_request.request_no},
            )
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                "support_requests:edit",
                kwargs={"request_no": self.support_request.request_no},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_mosque_staff_can_view_but_cannot_edit(self):
        self.client.force_login(self.mosque_staff)

        response = self.client.get(
            reverse(
                "support_requests:detail",
                kwargs={"request_no": self.support_request.request_no},
            )
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                "support_requests:edit",
                kwargs={"request_no": self.support_request.request_no},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_submit_creates_history(self):
        self.client.force_login(self.mosque_admin)

        response = self.client.post(
            reverse(
                "support_requests:submit",
                kwargs={"request_no": self.support_request.request_no},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.support_request.refresh_from_db()
        self.assertEqual(
            self.support_request.status,
            SupportRequestStatus.SUBMITTED,
        )
        self.assertEqual(
            SupportRequestHistory.objects.filter(
                support_request=self.support_request,
                to_status=SupportRequestStatus.SUBMITTED,
            ).count(),
            1,
        )

    def test_support_officer_can_request_documents(self):
        self.support_request.status = SupportRequestStatus.SUBMITTED
        self.support_request.save()

        self.client.force_login(self.support_officer)

        response = self.client.post(
            reverse(
                "support_requests:review_action",
                kwargs={"request_no": self.support_request.request_no},
            ),
            {
                "action": SupportRequestStatus.DOCUMENTS_REQUIRED,
                "approved_amount": "",
                "notes": "Please upload a quotation.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.support_request.refresh_from_db()
        self.assertEqual(
            self.support_request.status,
            SupportRequestStatus.DOCUMENTS_REQUIRED,
        )
        self.assertEqual(
            self.support_request.latest_admin_note,
            "Please upload a quotation.",
        )

    def test_rejection_requires_note(self):
        self.support_request.status = SupportRequestStatus.SUBMITTED
        self.support_request.save()

        self.client.force_login(self.support_officer)

        response = self.client.post(
            reverse(
                "support_requests:review_action",
                kwargs={"request_no": self.support_request.request_no},
            ),
            {
                "action": SupportRequestStatus.REJECTED,
                "approved_amount": "",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.support_request.refresh_from_db()
        self.assertEqual(
            self.support_request.status,
            SupportRequestStatus.SUBMITTED,
        )

    def test_district_officer_cannot_open_review_queue(self):
        User = get_user_model()
        district_officer = User.objects.create_user(
            username="district",
            email="district@example.com",
            password="StrongPass123!",
            role=UserRole.DISTRICT_OFFICER,
        )
        self.client.force_login(district_officer)

        response = self.client.get(
            reverse("support_requests:review_queue")
        )
        self.assertEqual(response.status_code, 403)


class SupportRequestCreationTests(TestCase):
    def test_unapproved_mosque_is_not_available_for_support_request(self):
        User = get_user_model()

        mosque_admin = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="StrongPass123!",
            role=UserRole.MOSQUE_ADMIN,
        )
        province = Province.objects.create(
            code="WP",
            name_en="Western Province",
        )
        district = District.objects.create(
            province=province,
            code="CMB",
            name_en="Colombo",
        )
        mosque = Mosque.objects.create(
            name_en="Pending Mosque",
            category="MASJID",
            province=province,
            district=district,
            address_line1="Test Road",
            city_or_town="Colombo",
            official_phone="0111111111",
            status=MosqueStatus.SUBMITTED,
            created_by=mosque_admin,
        )
        MosqueMembership.objects.create(
            mosque=mosque,
            user=mosque_admin,
            membership_role=MosqueMembershipRole.ADMIN,
            is_active=True,
            added_by=mosque_admin,
        )

        self.client.force_login(mosque_admin)
        response = self.client.get(reverse("support_requests:create"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Pending Mosque")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SUPPORT_SMS_BACKEND="support_requests.sms_backends.ConsoleSMSBackend",
)
class SupportNotificationWorkflowTests(SupportRequestFlowTests):
    def test_documents_required_notifies_mosque_admin_dashboard_email_and_mobile(self):
        self.support_request.status = SupportRequestStatus.SUBMITTED
        self.support_request.save()

        self.client.force_login(self.platform_admin)
        response = self.client.post(
            reverse(
                "support_requests:review_action",
                kwargs={"request_no": self.support_request.request_no},
            ),
            {
                "action": SupportRequestStatus.DOCUMENTS_REQUIRED,
                "approved_amount": "",
                "notes": "Upload two quotations and current roof photographs.",
            },
        )

        self.assertEqual(response.status_code, 302)

        notification = SupportNotification.objects.get(
            user=self.mosque_admin,
            support_request=self.support_request,
            notification_type=SupportNotificationType.DOCUMENTS_REQUIRED,
        )
        self.assertFalse(notification.is_read)
        self.assertIn("two quotations", notification.message)

        email_delivery = notification.deliveries.get(
            channel=NotificationChannel.EMAIL
        )
        sms_delivery = notification.deliveries.get(
            channel=NotificationChannel.SMS
        )
        self.assertEqual(email_delivery.status, NotificationDeliveryStatus.SENT)
        self.assertEqual(sms_delivery.status, NotificationDeliveryStatus.SENT)
        self.assertEqual(sms_delivery.recipient, "0771234567")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["mosqueadmin@example.com"])

        self.client.force_login(self.mosque_admin)
        dashboard = self.client.get(reverse("dashboard:mosque_admin"))
        self.assertContains(dashboard, "Additional information required")

    def test_approval_notifies_mosque_admin_dashboard_email_and_mobile(self):
        self.support_request.status = SupportRequestStatus.UNDER_REVIEW
        self.support_request.save()

        self.client.force_login(self.platform_admin)
        response = self.client.post(
            reverse(
                "support_requests:review_action",
                kwargs={"request_no": self.support_request.request_no},
            ),
            {
                "action": SupportRequestStatus.APPROVED,
                "approved_amount": "225000.00",
                "notes": "Approved after document verification.",
            },
        )

        self.assertEqual(response.status_code, 302)
        notification = SupportNotification.objects.get(
            user=self.mosque_admin,
            support_request=self.support_request,
            notification_type=SupportNotificationType.REQUEST_APPROVED,
        )
        self.assertIn("approved", notification.title.lower())
        self.assertEqual(
            notification.deliveries.filter(
                status=NotificationDeliveryStatus.SENT
            ).count(),
            2,
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_resubmission_returns_to_queue_and_notifies_platform_admin(self):
        self.support_request.status = SupportRequestStatus.DOCUMENTS_REQUIRED
        self.support_request.latest_admin_note = "Upload quotation."
        self.support_request.save()

        self.client.force_login(self.mosque_admin)
        response = self.client.post(
            reverse(
                "support_requests:submit",
                kwargs={"request_no": self.support_request.request_no},
            )
        )
        self.assertEqual(response.status_code, 302)

        self.support_request.refresh_from_db()
        self.assertEqual(
            self.support_request.status,
            SupportRequestStatus.SUBMITTED,
        )
        self.assertTrue(
            SupportNotification.objects.filter(
                user=self.platform_admin,
                support_request=self.support_request,
                notification_type=SupportNotificationType.REQUEST_RESUBMITTED,
            ).exists()
        )

    def test_notification_open_marks_it_read(self):
        notification = SupportNotification.objects.create(
            user=self.mosque_admin,
            support_request=self.support_request,
            notification_type=SupportNotificationType.DOCUMENTS_REQUIRED,
            title="Additional information required",
            message="Upload quotation.",
        )
        self.client.force_login(self.mosque_admin)

        response = self.client.get(
            reverse(
                "support_requests:notification_open",
                kwargs={"notification_id": notification.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserRole


class PlatformControlAccessTests(TestCase):
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

    def test_platform_admin_can_open_control_center(self):
        self.client.force_login(self.platform_admin)
        response = self.client.get(reverse("platform_control:overview"))
        self.assertEqual(response.status_code, 200)

    def test_mosque_admin_cannot_open_control_center(self):
        self.client.force_login(self.mosque_admin)
        response = self.client.get(reverse("platform_control:overview"))
        self.assertEqual(response.status_code, 403)

    def test_platform_admin_can_create_support_officer(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse("platform_control:user_create"),
            {
                "username": "support2",
                "first_name": "Support",
                "last_name": "Officer",
                "email": "support2@example.com",
                "phone_number": "0770000001",
                "role": UserRole.SUPPORT_OFFICER,
                "preferred_language": "en",
                "is_active": "on",
                "is_verified": "on",
                "password1": "StrongPass456!",
                "password2": "StrongPass456!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            get_user_model().objects.filter(
                username="support2",
                role=UserRole.SUPPORT_OFFICER,
            ).exists()
        )

    def test_platform_admin_cannot_create_platform_admin(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse("platform_control:user_create"),
            {
                "username": "platform2",
                "first_name": "Platform",
                "last_name": "Admin",
                "email": "platform2@example.com",
                "phone_number": "0770000002",
                "role": UserRole.PLATFORM_ADMIN,
                "preferred_language": "en",
                "is_active": "on",
                "is_verified": "on",
                "password1": "StrongPass456!",
                "password2": "StrongPass456!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username="platform2").exists()
        )

    def test_super_admin_can_create_platform_admin(self):
        User = get_user_model()
        super_admin = User.objects.create_superuser(
            username="super",
            email="super@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(super_admin)

        response = self.client.post(
            reverse("platform_control:user_create"),
            {
                "username": "platform3",
                "first_name": "Platform",
                "last_name": "Admin",
                "email": "platform3@example.com",
                "phone_number": "0770000003",
                "role": UserRole.PLATFORM_ADMIN,
                "preferred_language": "en",
                "is_active": "on",
                "is_verified": "on",
                "password1": "StrongPass456!",
                "password2": "StrongPass456!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(
                username="platform3",
                role=UserRole.PLATFORM_ADMIN,
            ).exists()
        )

    def test_platform_admin_cannot_edit_another_platform_admin(self):
        User = get_user_model()
        other_platform_admin = User.objects.create_user(
            username="platform_other",
            email="platform_other@example.com",
            password="StrongPass123!",
            role=UserRole.PLATFORM_ADMIN,
        )

        self.client.force_login(self.platform_admin)

        response = self.client.get(
            reverse(
                "platform_control:user_edit",
                kwargs={"user_id": other_platform_admin.pk},
            )
        )
        self.assertEqual(response.status_code, 403)


class NotificationMonitorTests(TestCase):
    def test_platform_admin_can_open_delivery_monitor(self):
        User = get_user_model()
        platform_admin = User.objects.create_user(
            username="platform_monitor",
            email="platform_monitor@example.com",
            password="StrongPass123!",
            role=UserRole.PLATFORM_ADMIN,
        )

        self.client.force_login(platform_admin)
        response = self.client.get(
            reverse("platform_control:notification_delivery_monitor")
        )
        self.assertEqual(response.status_code, 200)

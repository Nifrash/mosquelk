import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _digits_only(value):
    return re.sub(r"\D", "", value or "")


class ConsoleSMSBackend:
    """Development SMS backend. Logs the message instead of contacting a paid SMS gateway."""

    provider_name = "console"

    def send_message(self, to, message):
        logger.info("SMS to %s: %s", to, message)
        print(f"[SMS console] To: {to} | {message}")
        return "console-delivery"


class DisabledSMSBackend:
    provider_name = "disabled"

    def send_message(self, to, message):
        raise RuntimeError("SMS delivery is disabled.")


class TextLKSMSBackend:
    """
    Production SMS backend for Text.lk.

    Uses Text.lk's recommended Bearer-token POST API:
        POST https://app.text.lk/api/v3/sms/send
    """

    provider_name = "text.lk"

    def send_message(self, to, message):
        api_token = (getattr(settings, "TEXTLK_API_TOKEN", "") or "").strip()
        sender_id = (getattr(settings, "TEXTLK_SENDER_ID", "") or "").strip()
        api_url = (
            getattr(
                settings,
                "TEXTLK_API_URL",
                "https://app.text.lk/api/v3/sms/send",
            )
            or ""
        ).strip()
        timeout = int(getattr(settings, "TEXTLK_TIMEOUT_SECONDS", 20))
        dlt_template_id = (
            getattr(settings, "TEXTLK_DLT_TEMPLATE_ID", "") or ""
        ).strip()

        if not api_token:
            raise RuntimeError("TEXTLK_API_TOKEN is not configured.")
        if not sender_id:
            raise RuntimeError("TEXTLK_SENDER_ID is not configured.")
        if not api_url:
            raise RuntimeError("TEXTLK_API_URL is not configured.")

        recipient = _digits_only(to)

        # Text.lk examples use international format without '+'.
        # Convert a local Sri Lankan number such as 0712345678 -> 94712345678.
        if recipient.startswith("0"):
            country_code = _digits_only(
                getattr(settings, "SMS_DEFAULT_COUNTRY_CODE", "+94")
            )
            recipient = country_code + recipient[1:]

        if not recipient:
            raise RuntimeError("SMS recipient is empty.")

        payload = {
            "recipient": recipient,
            "sender_id": sender_id,
            "type": "plain",
            "message": str(message),
        }

        if dlt_template_id:
            payload["dlt_template_id"] = dlt_template_id

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Text.lk connection failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError:
            data = {
                "status": False,
                "message": response.text[:500],
            }

        if not response.ok:
            raise RuntimeError(
                f"Text.lk HTTP {response.status_code}: "
                f"{data.get('message') or response.text[:300]}"
            )

        status = data.get("status")
        success = (
            status is True
            or str(status).strip().lower()
            in {"true", "success", "queued", "ok"}
        )

        if not success:
            raise RuntimeError(
                f"Text.lk rejected SMS: "
                f"{data.get('message') or data}"
            )

        message_id = ""
        if isinstance(data.get("data"), dict):
            message_id = (
                data["data"].get("sms_id")
                or data["data"].get("uid")
                or ""
            )

        logger.info(
            "Text.lk SMS accepted for %s, id=%s",
            recipient,
            message_id or "n/a",
        )

        return message_id or data.get("message") or "textlk-accepted"

import logging

logger = logging.getLogger(__name__)


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

"""
Slack Incoming Webhook helper.

Sends formatted block-kit alerts to a configured Slack channel.
Requires SLACK_WEBHOOK_URL to be set; silently skips if unset.
"""

import structlog
import httpx

from app.config import settings

logger = structlog.get_logger()


async def send_slack_alert(
    title: str,
    fields: list[dict[str, str]],
    message: str | None = None,
    notify_here: bool = False,
) -> None:
    """
    Post a formatted alert to Slack via Incoming Webhook.

    Args:
        title:        Header text shown at the top of the message.
        fields:       List of {"label": str, "value": str} dicts rendered as key/value pairs.
        message:      Optional body text appended below the fields (supports mrkdwn).
        notify_here:  When True, prepends <!here> to notify all active channel members.

    Silently returns if SLACK_WEBHOOK_URL is not configured.
    Never raises — Slack failures must not affect the calling endpoint.
    """
    if not settings.slack_webhook_url:
        logger.warning("slack_alert_skipped", reason="SLACK_WEBHOOK_URL not configured")
        return

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title, "emoji": True},
        },
    ]

    if notify_here:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "<!here>"}}
        )

    blocks.append(
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{f['label']}*\n`{f['value']}`"}
                for f in fields
            ],
        }
    )

    if message:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": message}}
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                settings.slack_webhook_url,
                json={"blocks": blocks},
            )
            resp.raise_for_status()
        logger.info("slack_alert_sent", title=title)
    except Exception as exc:
        logger.warning("slack_alert_failed", error=str(exc))

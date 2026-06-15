"""
User Context - Fetches a user's health profile, connected devices, and latest
wearable (Spike) biometrics from the user_service microservice REST API, and
formats them for prompt injection.

Calls user_service over HTTP (not its database) so the service boundary and
schema stay owned by user_service. Authenticated with a short-lived service
JWT signed with the shared TOKEN_SECRET (Buildly RAD Core pattern).

Fail-safe: any error (service down, auth, missing user) returns None / "" so
the chat flow is never broken; the profile block is only added when available.
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

# Base URL of the user_service microservice, e.g. http://localhost:8001
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "").rstrip("/")
# Shared secret used to sign the service JWT (matches user_service TOKEN_SECRET).
USER_SERVICE_TOKEN_SECRET = os.getenv("USER_SERVICE_TOKEN_SECRET", "")
# How long the minted service token is valid (seconds).
_TOKEN_TTL = 300
_HTTP_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


def resolve_identity(authorization: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Extract (core_user_uuid, raw_token) from an incoming Bearer JWT.

    The identity is taken from the signed token, never from client-supplied
    request fields, so a caller cannot request another user's health data.
    Returns (None, None) when no usable identity is present.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None, None
    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        return None, None

    try:
        import jwt
    except ImportError:
        logger.warning("PyJWT not installed; cannot verify identity token")
        return None, None

    payload = None
    if USER_SERVICE_TOKEN_SECRET:
        try:
            payload = jwt.decode(token, USER_SERVICE_TOKEN_SECRET, algorithms=["HS256"])
        except Exception as e:
            logger.warning("Identity token verification failed: %s", e)

    if payload is None:
        # Dev-only escape hatch: accept unverified tokens when explicitly enabled.
        if os.getenv("ALLOW_UNVERIFIED_JWT", "false").lower() == "true":
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
            except Exception as e:
                logger.warning("Unverified token decode failed: %s", e)
                return None, None
        else:
            return None, None

    return payload.get("core_user_uuid"), token


def _mint_service_token(core_user_uuid: str) -> Optional[str]:
    """Mint a short-lived JWT carrying core_user_uuid for user_service auth."""
    if not USER_SERVICE_TOKEN_SECRET:
        return None
    try:
        import jwt
    except ImportError:
        logger.warning("PyJWT not installed; cannot authenticate to user_service")
        return None

    payload = {
        "core_user_uuid": core_user_uuid,
        "username": "babblebeaver-service",
        "exp": int(time.time()) + _TOKEN_TTL,
    }
    return jwt.encode(payload, USER_SERVICE_TOKEN_SECRET, algorithm="HS256")


async def fetch_user_context(
    core_user_uuid: str, bearer_token: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Fetch profile + connected providers + latest biometrics over HTTP.

    Args:
        core_user_uuid: identity to fetch context for.
        bearer_token: optional end-user JWT to forward; if omitted a service
            token is minted from USER_SERVICE_TOKEN_SECRET.
    """
    if not USER_SERVICE_URL or not core_user_uuid:
        return None

    token = bearer_token or _mint_service_token(core_user_uuid)
    if not token:
        logger.warning("No token available for user_service; skipping context")
        return None

    headers = {"Authorization": f"Bearer {token}"}
    params = {"core_user_uuid": core_user_uuid}

    try:
        async with httpx.AsyncClient(
            base_url=USER_SERVICE_URL, headers=headers, timeout=_HTTP_TIMEOUT
        ) as client:
            profile_resp = await client.get("/userprofile/", params=params)
            if profile_resp.status_code != 200:
                logger.warning(
                    "user_service /userprofile returned %s", profile_resp.status_code
                )
                return None
            profiles = profile_resp.json()
            # DRF list endpoint may paginate; handle list or {results: [...]}.
            if isinstance(profiles, dict):
                profiles = profiles.get("results", [])
            if not profiles:
                return None
            profile = profiles[0]

            signals_resp = await client.get(
                "/body-signals/", params={**params, "period": "month"}
            )
            biometrics = signals_resp.json() if signals_resp.status_code == 200 else {}

            providers_resp = await client.get("/connectedprovider/", params=params)
            providers = (
                providers_resp.json() if providers_resp.status_code == 200 else []
            )
            if isinstance(providers, dict):
                providers = providers.get("results", [])
    except Exception as e:
        logger.warning("Failed to fetch user context from user_service: %s", e)
        return None

    return {
        # Full profile passthrough — any new field added to user_service's
        # UserProfile shows up here automatically, no code change required.
        "profile": profile if isinstance(profile, dict) else {},
        "connected_providers": [
            p.get("provider_slug") for p in providers if p.get("provider_slug")
        ],
        "biometrics": biometrics if isinstance(biometrics, dict) else {},
    }


# Internal/plumbing fields that should never be surfaced to the prompt.
_PROFILE_SKIP_FIELDS = {
    "id", "user_uuid", "core_user_uuid", "created_at", "updated_at",
    "push_token", "user",
    # Notification toggles — not relevant to nutrition reasoning.
    "push_notifications_enabled", "email_alerts_enabled",
    "dhub_notifications_enabled",
}
# Preferred ordering for known fields; anything else is appended afterwards.
_PROFILE_FIELD_ORDER = [
    "full_name", "glp1_medication", "dietary_preferences", "health_goals",
    "is_nutritionist", "is_premium",
]


def format_user_context(ctx: Optional[Dict[str, Any]]) -> str:
    """Render the context dict into a prompt block. Empty string if no data.

    Schema-agnostic: every non-empty profile field returned by user_service is
    surfaced, so new fields (location, weather prefs, MAI signals, etc.) appear
    automatically without changing this code.
    """
    if not ctx:
        return ""

    profile = ctx.get("profile") or {}
    lines = ["USER HEALTH PROFILE:"]

    ordered_keys = [k for k in _PROFILE_FIELD_ORDER if k in profile]
    ordered_keys += [k for k in profile if k not in _PROFILE_FIELD_ORDER]

    for key in ordered_keys:
        if key in _PROFILE_SKIP_FIELDS:
            continue
        value = profile.get(key)
        if not _has_value(value):
            continue
        lines.append(f"- {_humanize(key)}: {_compact(value)}")

    if ctx.get("connected_providers"):
        lines.append(f"- Connected Devices: {', '.join(ctx['connected_providers'])}")

    bios = ctx.get("biometrics") or {}
    if bios:
        readings = ", ".join(
            f"{sig}={_fmt_num(d.get('value'))}{d.get('unit', '')}"
            for sig, d in bios.items()
            if isinstance(d, dict)
        )
        as_of = next(
            (d.get("recorded_at", "")[:10] for d in bios.values() if isinstance(d, dict)),
            "",
        )
        if readings:
            lines.append(f"- Recent Biometrics (as of {as_of}): {readings}")

    # Only a header and nothing else means no usable data.
    return "\n".join(lines) if len(lines) > 1 else ""


def _has_value(value: Any) -> bool:
    """True if a field holds meaningful data worth showing the model."""
    if value is None:
        return False
    if isinstance(value, bool):
        # Only surface flags that are on (e.g. "Nutritionist: True"); a False
        # flag is noise.
        return value
    if isinstance(value, str):
        return value.strip() not in ("", '""')
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _humanize(key: str) -> str:
    """snake_case -> Title Case, with a few nicer special cases."""
    overrides = {
        "glp1_medication": "GLP-1 Medication",
        "full_name": "Name",
        "is_nutritionist": "Nutritionist",
        "is_premium": "Premium Member",
        "mai_signals": "MAI Signals",
    }
    return overrides.get(key, key.replace("_", " ").title())


def _compact(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(", ", ": "))
    return str(value)


def _fmt_num(v: Any) -> str:
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(f)
    except (TypeError, ValueError):
        return str(v)

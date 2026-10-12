from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.exceptions import AppError

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    configured_token = settings.banking_api_token
    if (
        credentials is None
        or not configured_token
        or not hmac.compare_digest(credentials.credentials, configured_token)
    ):
        raise AppError(401, "UNAUTHORIZED", "Missing or invalid bearer token.")
    return credentials.credentials

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.auth.accounts import AccountError
from app.auth.errors import AuthError

router = APIRouter(prefix="/v1", tags=["accounts"])


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    trainer_name: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=1, max_length=32, repr=False)
    confirmation: str = Field(min_length=1, max_length=32, repr=False)
    access_code: str = Field(min_length=1, max_length=128, repr=False)


class RegistrationResponse(BaseModel):
    trainer_id: UUID
    status: str


def account_service(container: ApiContainer = Depends(get_api_container)):
    service = container.account_service
    if service is None or not service.enabled:
        raise api_error(
            503, "ACCOUNTS_UNAVAILABLE", "Account management is unavailable."
        )
    return service


def invoke(action):
    try:
        return action()
    except AccountError as exc:
        raise api_error(
            exc.status, exc.code, "Account request could not be completed."
        ) from None
    except AuthError:
        raise api_error(
            503, "ACCOUNTS_UNAVAILABLE", "Account management is unavailable."
        ) from None


@router.post("/auth/register", response_model=RegistrationResponse)
def register(
    payload: RegistrationRequest,
    request: Request,
    key: UUID = Header(alias="Idempotency-Key"),
    service=Depends(account_service),
):
    def action():
        host = request.client.host if request.client else "unknown"
        service.throttle("register-ip", host, 8, 3600)
        service.throttle("register-total", "global", 100, 3600)
        return service.register(
            key,
            payload.trainer_name,
            payload.pin,
            payload.confirmation,
            payload.access_code,
        )

    return invoke(action)

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ApiContainer, get_api_container
from app.api.errors import api_error
from app.auth.accounts import AccountError
from app.auth.errors import AuthError
from app.auth.errors import InvalidCredentialsError
from app.api.security import require_enabled_principal, require_admin_principal

router = APIRouter(prefix="/v1", tags=["accounts"])


class AccountCapabilities(BaseModel):
    enabled: bool


@router.get("/auth/account-capabilities", response_model=AccountCapabilities)
def account_capabilities(container: ApiContainer = Depends(get_api_container)):
    return {
        "enabled": bool(container.account_service and container.account_service.enabled)
    }


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
    except InvalidCredentialsError:
        raise api_error(400, "INVALID_CURRENT_PIN", "Invalid credentials.") from None
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


class ProfileResponse(BaseModel):
    trainer_id: UUID
    display_name: str
    photo_url: str | None = None
    revision: int | None = None


class ProfilePage(BaseModel):
    items: list[ProfileResponse]
    offset: int
    has_more: bool


class RenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    display_name: str = Field(min_length=1, max_length=64)
    expected_revision: int = Field(ge=0, strict=True)


class ProfileReceipt(BaseModel):
    trainer_id: UUID
    revision: int


class PinChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    current_pin: str = Field(pattern=r"^[0-9]{4}$", repr=False)
    new_pin: str = Field(pattern=r"^[0-9]{4}$", repr=False)
    confirmation: str = Field(pattern=r"^[0-9]{4}$", repr=False)


class PinChangeResponse(BaseModel):
    status: str
    sign_in_required: bool


@router.get("/accounts", response_model=ProfilePage)
def profiles(
    offset: int = Query(default=0, ge=0, le=100000),
    principal=Depends(require_enabled_principal),
    service=Depends(account_service),
):
    return invoke(lambda: service.profiles(principal.trainer_id, offset))


@router.get("/accounts/{trainer_id}", response_model=ProfileResponse)
def profile(
    trainer_id: UUID,
    principal=Depends(require_enabled_principal),
    service=Depends(account_service),
):
    return invoke(lambda: service.profile(str(trainer_id), principal.trainer_id))


@router.put("/account/name", response_model=ProfileReceipt)
def rename(
    payload: RenameRequest,
    key: UUID = Header(alias="Idempotency-Key"),
    principal=Depends(require_enabled_principal),
    service=Depends(account_service),
):
    return invoke(
        lambda: service.rename(
            principal.trainer_id, key, payload.expected_revision, payload.display_name
        )
    )


@router.put("/account/photo", response_model=ProfileReceipt)
async def photo(
    request: Request,
    expected_revision: int = Query(ge=0),
    key: UUID = Header(alias="Idempotency-Key"),
    principal=Depends(require_enabled_principal),
    service=Depends(account_service),
):
    if request.headers.get("Content-Type", "").split(";")[0] not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        raise api_error(422, "INVALID_PHOTO", "Unsupported image.")
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 5 * 1024 * 1024:
            raise api_error(413, "INVALID_PHOTO", "Image exceeds maximum size.")
    return invoke(
        lambda: service.photo(
            principal.trainer_id, key, expected_revision, bytes(content)
        )
    )


@router.post("/account/pin", response_model=PinChangeResponse)
def change_pin(
    payload: PinChangeRequest,
    key: UUID = Header(alias="Idempotency-Key"),
    principal=Depends(require_enabled_principal),
    service=Depends(account_service),
):
    def action():
        service.throttle("change-pin", principal.trainer_id, 8, 3600)
        return service.change_pin(
            principal.trainer_id,
            key,
            payload.current_pin,
            payload.new_pin,
            payload.confirmation,
        )

    return invoke(action)


@router.post("/auth/pin-change/resume", response_model=PinChangeResponse)
def resume_pin(
    payload: PinChangeRequest,
    request: Request,
    key: UUID = Header(alias="Idempotency-Key"),
    service=Depends(account_service),
):
    # Only a previously authenticated intent, unguessable key AND exact secret
    # request body can resume. This path cannot originate a credential change.
    def action():
        service.throttle(
            "pin-resume-ip",
            request.client.host if request.client else "unknown",
            8,
            3600,
        )
        service.throttle("pin-resume-op", str(key), 8, 3600)
        return service.change_pin(
            None,
            key,
            payload.current_pin,
            payload.new_pin,
            payload.confirmation,
            resume=True,
        )

    return invoke(action)


class AdminAccount(BaseModel):
    trainer_id: UUID
    display_name: str
    globally_enabled: bool
    is_admin: bool
    revision: int
    provisioned: bool


class AdminAccountPage(BaseModel):
    items: list[AdminAccount]
    offset: int
    has_more: bool


class AccountStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)
    enabled: bool = Field(strict=True)


class AccountStatusReceipt(ProfileReceipt):
    globally_enabled: bool


class ResetPinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    new_pin: str = Field(pattern=r"^[0-9]{4}$", repr=False)
    confirmation: str = Field(pattern=r"^[0-9]{4}$", repr=False)


@router.get("/admin/accounts", response_model=AdminAccountPage)
def admin_accounts(
    offset: int = Query(0, ge=0, le=100000),
    principal=Depends(require_admin_principal),
    service=Depends(account_service),
):
    return invoke(lambda: service.admin_accounts(principal.trainer_id, offset))


@router.put("/admin/accounts/{trainer_id}/status", response_model=AccountStatusReceipt)
def admin_status(
    trainer_id: UUID,
    payload: AccountStatusRequest,
    key: UUID = Header(alias="Idempotency-Key"),
    principal=Depends(require_admin_principal),
    service=Depends(account_service),
):
    return invoke(
        lambda: service.admin_status(
            principal.trainer_id,
            str(trainer_id),
            key,
            payload.expected_revision,
            payload.enabled,
        )
    )


@router.post("/admin/accounts/{trainer_id}/reset-pin", response_model=PinChangeResponse)
def reset_pin(
    trainer_id: UUID,
    payload: ResetPinRequest,
    key: UUID = Header(alias="Idempotency-Key"),
    principal=Depends(require_admin_principal),
    service=Depends(account_service),
):
    if str(trainer_id) == principal.trainer_id:
        raise api_error(403, "ACCOUNT_FORBIDDEN", "Use your personal PIN change.")

    def action():
        service.throttle("admin-reset", principal.trainer_id, 10, 3600)
        return service.change_pin(
            principal.trainer_id,
            key,
            "",
            payload.new_pin,
            payload.confirmation,
            target=str(trainer_id),
        )

    return invoke(action)

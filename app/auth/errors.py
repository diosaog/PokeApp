from __future__ import annotations


class AuthError(RuntimeError):
    code = "AUTH_ERROR"
    public_code = "INVALID_CREDENTIALS"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class MissingAuthPepperError(AuthError):
    code = "AUTH_PEPPER_MISSING"
    public_code = "AUTH_UNAVAILABLE"

    def __init__(self) -> None:
        super().__init__("Auth pepper is not configured.")


class InvalidCredentialsError(AuthError):
    code = "INVALID_CREDENTIALS"
    public_code = "INVALID_CREDENTIALS"

    def __init__(self) -> None:
        super().__init__("Invalid credentials.")


class AuthNotProvisionedError(AuthError):
    code = "AUTH_NOT_PROVISIONED"
    public_code = "INVALID_CREDENTIALS"

    def __init__(self, trainer_id: str) -> None:
        self.trainer_id = trainer_id
        super().__init__("Trainer auth is not provisioned.")


class AuthIdentityMismatchError(AuthError):
    code = "AUTH_IDENTITY_MISMATCH"
    public_code = "INVALID_CREDENTIALS"

    def __init__(self, trainer_id: str) -> None:
        self.trainer_id = trainer_id
        super().__init__("Supabase Auth user did not match trainer mapping.")


class AuthBackendError(AuthError):
    code = "AUTH_BACKEND_ERROR"
    public_code = "AUTH_UNAVAILABLE"

    def __init__(self, message: str = "Auth backend failed.") -> None:
        super().__init__(message)


class ProvisioningError(AuthError):
    code = "AUTH_PROVISIONING_ERROR"
    public_code = "AUTH_UNAVAILABLE"


class ProvisioningPermissionError(ProvisioningError):
    code = "AUTH_PROVISIONING_FORBIDDEN"

    def __init__(self) -> None:
        super().__init__("Provisioning requires an explicitly privileged path.")


class PartialProvisioningError(ProvisioningError):
    code = "AUTH_PARTIAL_PROVISION"

    def __init__(self, *, trainer_id: str, auth_user_id: str) -> None:
        self.trainer_id = trainer_id
        self.auth_user_id = auth_user_id
        super().__init__("Auth user was created, but trainer mapping was not confirmed.")

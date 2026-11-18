"""Errores de dominio del sandbox transaccional. El API los mapea a HTTP."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class EmailAlreadyRegistered(DomainError):
    status_code = 409


class InvalidCredentials(DomainError):
    status_code = 401


class InvalidRole(DomainError):
    status_code = 400


class AccountNotFound(DomainError):
    status_code = 404


class AccountNotActive(DomainError):
    status_code = 409


class UserAccountMissing(DomainError):
    status_code = 404


class InsufficientFunds(DomainError):
    status_code = 409


class InvalidTransfer(DomainError):
    status_code = 400


class ForbiddenAction(DomainError):
    status_code = 403


class SupervisionNotFound(DomainError):
    status_code = 404


class SupervisionConflict(DomainError):
    status_code = 409


class UnlinkNotConfirmed(DomainError):
    status_code = 400

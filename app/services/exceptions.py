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


class PatternPause(DomainError):
    """Pausa consciente: compras seguidas o monto fuera del ticket habitual."""

    status_code = 409

    def __init__(self, payload: dict) -> None:
        self.detail = payload
        Exception.__init__(self, str(payload.get("mensaje", "Patrón de gasto")))


class ImpulsiveSpend(DomainError):
    """Alerta pedagógica. El débito no se registra hasta forzar la confirmación."""

    status_code = 409

    def __init__(self, payload: dict) -> None:
        self.detail = payload
        Exception.__init__(self, str(payload.get("mensaje", "Gasto impulsivo")))


class GoalNotFound(DomainError):
    status_code = 404


class GoalNotActive(DomainError):
    status_code = 409


class GoalDepositExceedsTarget(DomainError):
    status_code = 400


class ModuleNotFound(DomainError):
    status_code = 404


class QuizAnswerIncorrect(DomainError):
    status_code = 400


class SeniorNotLinkable(DomainError):
    status_code = 400


class FamilyTaken(DomainError):
    status_code = 409


class InvitationNotFound(DomainError):
    status_code = 404


class CardBlocked(DomainError):
    status_code = 409

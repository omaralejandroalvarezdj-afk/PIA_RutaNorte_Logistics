"""Excepciones del dominio, expresadas en lenguaje del negocio."""


class DomainException(Exception):
    """Excepción base para errores de la lógica de negocio."""


class InvalidOrderData(DomainException):
    """Los datos de entrada o montos violan las reglas del negocio."""


class InvalidOrderTransition(DomainException):
    """Se intentó una transición de estado prohibida por el ciclo operativo."""


class WeightDiscrepancyDetected(DomainException):
    """El peso real excede la tolerancia permitida (>15%) respecto a lo cotizado."""


class EntityNotFound(DomainException):
    """No existe la entidad solicitada (orden, cliente, ...)."""


class DuplicateEntity(DomainException):
    """Ya existe una entidad con el mismo identificador."""


class CreditoBloqueado(DomainException):
    """El cliente corporativo supera el límite de morosidad (US-13 / RN-12)."""

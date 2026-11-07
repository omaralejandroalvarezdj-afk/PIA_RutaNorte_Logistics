from decimal import Decimal

import pytest

from src.domain.models import Cliente, Cotizacion, Money, OrdenServicio, Ruta
from src.domain.specifications import (
    AndSpecification,
    ClienteActivoSpecification,
    ClientePreferenteSpecification,
    MontoMinimoSpecification,
    NotSpecification,
    OrSpecification,
    PromocionActivaSpecification,
    Specification,
)


def orden(total="2000", activo=True, preferente=False, promo=False):
    return OrdenServicio.registrar(
        "ORD-1",
        Cliente("C-1", "Cliente", activo=activo, es_preferente=preferente),
        Ruta("A", "B", 10),
        Cotizacion(Money(Decimal(total)), Money(Decimal(total))),
        promocion_activa=promo,
    )


def test_cliente_activo():
    assert ClienteActivoSpecification().is_satisfied_by(orden(activo=True))
    assert not ClienteActivoSpecification().is_satisfied_by(orden(activo=False))


def test_monto_minimo_limite_1500():
    spec = MontoMinimoSpecification()
    assert spec.is_satisfied_by(orden(total="1500"))
    assert spec.is_satisfied_by(orden(total="1500.01"))
    assert not spec.is_satisfied_by(orden(total="1499.99"))


def test_monto_minimo_personalizado():
    assert MontoMinimoSpecification(Decimal("100")).is_satisfied_by(orden(total="100"))


def test_promocion_activa_y_preferente():
    assert PromocionActivaSpecification().is_satisfied_by(orden(promo=True))
    assert not PromocionActivaSpecification().is_satisfied_by(orden())
    assert ClientePreferenteSpecification().is_satisfied_by(orden(preferente=True))


def test_operadores_producen_composites():
    a, b = ClienteActivoSpecification(), MontoMinimoSpecification()
    assert isinstance(a & b, AndSpecification)
    assert isinstance(a | b, OrSpecification)
    assert isinstance(~a, NotSpecification)
    assert isinstance(a & b, Specification)


@pytest.mark.parametrize("activo,total,esperado", [(True, "2000", True), (True, "100", False), (False, "2000", False)])
def test_and(activo, total, esperado):
    spec = ClienteActivoSpecification() & MontoMinimoSpecification()
    assert spec.is_satisfied_by(orden(total=total, activo=activo)) is esperado


@pytest.mark.parametrize("activo,total,esperado", [(True, "100", True), (False, "2000", True), (False, "100", False)])
def test_or(activo, total, esperado):
    spec = ClienteActivoSpecification() | MontoMinimoSpecification()
    assert spec.is_satisfied_by(orden(total=total, activo=activo)) is esperado


def test_not_y_doble_negacion():
    o = orden(promo=True)
    assert not (~PromocionActivaSpecification()).is_satisfied_by(o)
    assert (~~PromocionActivaSpecification()).is_satisfied_by(o)


@pytest.mark.parametrize(
    "preferente,total,promo,esperado",
    [
        (True, "1500", False, True),   # cumple todo
        (True, "1499.99", False, False),  # monto insuficiente
        (True, "3000", True, False),   # promoción activa bloquea el beneficio
        (False, "3000", False, False),  # no preferente
    ],
)
def test_beneficio_referencia_preferente_and_monto_and_not_promocion(preferente, total, promo, esperado):
    assert orden(total=total, preferente=preferente, promo=promo).cumple_beneficio_referencia() is esperado


def test_repr_legible_de_composicion():
    spec = ClientePreferenteSpecification() & MontoMinimoSpecification() & ~PromocionActivaSpecification()
    assert repr(spec) == "((ClientePreferente AND MontoMinimo(>=1500)) AND NOT PromocionActiva)"
    assert repr(ClienteActivoSpecification() | ClienteActivoSpecification()) == "(ClienteActivo OR ClienteActivo)"


def test_operador_con_tipo_incorrecto_no_es_soportado():
    with pytest.raises(TypeError):
        ClienteActivoSpecification() & 5
    with pytest.raises(TypeError):
        ClienteActivoSpecification() | "x"

from decimal import Decimal

import pytest

from src.domain.models import (
    Cliente,
    Cotizacion,
    EvidenciaPOD,
    Money,
    Operador,
    OrderStatus,
    OrdenServicio,
    Ruta,
    Vehiculo,
)
from src.infrastructure.repositories import (
    SqlAlchemyClienteRepository,
    SqlAlchemyOperadorRepository,
    SqlAlchemyOrdenServicioRepository,
    SqlAlchemyVehiculoRepository,
)
from src.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def nueva_orden(oid="ORD-DB-001", cliente=None):
    cliente = cliente or Cliente("C-99", "Logística del Norte SA", es_preferente=True, es_corporativo=True)
    return OrdenServicio.registrar(
        oid,
        cliente,
        Ruta("Monterrey", "Nuevo Laredo", 220.0),
        Cotizacion(Money(Decimal("5000.00")), Money(Decimal("5800.00")), 5.0),
        promocion_activa=True,
    )


def test_cliente_vehiculo_operador_roundtrip(session_factory):
    s = session_factory()
    clientes, vehiculos, operadores = (
        SqlAlchemyClienteRepository(s),
        SqlAlchemyVehiculoRepository(s),
        SqlAlchemyOperadorRepository(s),
    )
    clientes.guardar(Cliente("C-1", "Uno SA", es_corporativo=True, activo=False, es_preferente=True))
    vehiculos.guardar(Vehiculo("V-1", "ABC-123", "Caja Seca"))
    operadores.guardar(Operador("OP-1", "Rigoberto", disponible=False))
    s.commit()
    s.close()

    s = session_factory()
    c = SqlAlchemyClienteRepository(s).buscar_por_id("C-1")
    assert (c.razon_social, c.es_corporativo, c.activo, c.es_preferente) == ("Uno SA", True, False, True)
    assert SqlAlchemyVehiculoRepository(s).buscar_por_placas("ABC-123").id == "V-1"
    assert SqlAlchemyOperadorRepository(s).buscar_por_id("OP-1").disponible is False
    assert SqlAlchemyClienteRepository(s).buscar_por_id("NO") is None
    assert SqlAlchemyVehiculoRepository(s).buscar_por_id("NO") is None
    assert SqlAlchemyVehiculoRepository(s).buscar_por_placas("NO") is None
    assert SqlAlchemyOperadorRepository(s).buscar_por_id("NO") is None
    s.close()


def test_actualizar_entidad_existente(session_factory):
    s = session_factory()
    repo = SqlAlchemyClienteRepository(s)
    repo.guardar(Cliente("C-1", "Uno SA"))
    repo.guardar(Cliente("C-1", "Uno SA de CV", activo=False))
    s.commit()
    assert repo.buscar_por_id("C-1").razon_social == "Uno SA de CV"
    assert repo.buscar_por_id("C-1").activo is False


def test_orden_conserva_todos_sus_datos(session_factory):
    """Regresión: antes se perdían cliente.activo, subtotal, vehículo, operador y POD."""
    s = session_factory()
    SqlAlchemyClienteRepository(s).guardar(Cliente("C-99", "Logística del Norte SA", es_preferente=True, es_corporativo=True))
    repo = SqlAlchemyOrdenServicioRepository(s)
    orden = nueva_orden()
    repo.guardar(orden)
    s.commit()

    orden = repo.buscar_por_id("ORD-DB-001")
    orden.confirmar_cotizacion()
    v, o = Vehiculo("V-1", "ABC-123", "Caja"), Operador("OP-1", "Juan")
    SqlAlchemyVehiculoRepository(s).guardar(v)
    SqlAlchemyOperadorRepository(s).guardar(o)
    orden.asignar_recursos(v, o)
    orden.validar_recoleccion(100, 100)
    orden.registrar_entrega(EvidenciaPOD("firma", "ine123", ["a.jpg", "b.jpg"]))
    repo.guardar(orden)
    s.commit()
    s.close()

    s = session_factory()
    r = SqlAlchemyOrdenServicioRepository(s).buscar_por_id("ORD-DB-001")
    assert r.status == OrderStatus.DELIVERED
    assert r.cliente.es_preferente and r.cliente.es_corporativo
    assert r.cotizacion.subtotal.amount == Decimal("5000.00")
    assert r.cotizacion.total.amount == Decimal("5800.00")
    assert r.cotizacion.porcentaje_descuento == 5.0
    assert r.promocion_activa is True
    assert (r.vehiculo.placas, r.operador.nombre) == ("ABC-123", "Juan")
    assert r.evidencia_pod.fotografias == ["a.jpg", "b.jpg"] and r.evidencia_pod.ine == "ine123"
    s.close()


def test_buscar_orden_inexistente(session_factory):
    s = session_factory()
    assert SqlAlchemyOrdenServicioRepository(s).buscar_por_id("NADA") is None


def test_unit_of_work_commit(session_factory):
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.clientes.guardar(Cliente("C-99", "Logística del Norte SA"))
        uow.ordenes.guardar(nueva_orden("ORD-UOW-1"))
        uow.commit()
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.ordenes.buscar_por_id("ORD-UOW-1") is not None


def test_unit_of_work_rollback_ante_excepcion(session_factory):
    with pytest.raises(RuntimeError):
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            uow.clientes.guardar(Cliente("C-99", "Logística del Norte SA"))
            uow.ordenes.guardar(nueva_orden("ORD-UOW-2"))
            raise RuntimeError("falla simulada antes del commit")
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.ordenes.buscar_por_id("ORD-UOW-2") is None
        assert uow.clientes.buscar_por_id("C-99") is None


def test_unit_of_work_sin_commit_descarta_cambios(session_factory):
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.clientes.guardar(Cliente("C-5", "Sin commit"))
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.clientes.buscar_por_id("C-5") is None


def test_unit_of_work_publica_eventos_solo_despues_del_commit(session_factory):
    publicados = []
    with SqlAlchemyUnitOfWork(session_factory, publicados.append) as uow:
        uow.clientes.guardar(Cliente("C-99", "Logística del Norte SA"))
        uow.ordenes.guardar(nueva_orden("ORD-EV-1"))
        assert publicados == []  # aún no hay COMMIT
        uow.commit()
    assert [e.name for e in publicados] == ["OrdenRegistrada"]
    assert [e.name for e in uow.published_events] == ["OrdenRegistrada"]


def test_unit_of_work_rollback_sin_sesion():
    uow = SqlAlchemyUnitOfWork(lambda: None)
    uow.rollback()  # no debe fallar si nunca se abrió

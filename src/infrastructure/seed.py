"""Datos de demostración (idempotente). Se desactiva con SEED_DEMO=0."""
from src.domain.models import Cliente, Operador, Vehiculo

CLIENTES = [
    Cliente("CLI-001", "Industrial Regiomontana SA", es_corporativo=True, es_preferente=True),
    Cliente("CLI-002", "Transportes del Bajío SA (crédito vencido)", es_corporativo=True, dias_morosidad=45),
    Cliente("CLI-003", "Abarrotes La Esperanza (ocasional)"),
    Cliente("CLI-004", "Cliente inactivo SA", activo=False),
]
VEHICULOS = [
    Vehiculo("V-01", "NL-4821-A", "Rabón"),
    Vehiculo("V-02", "NL-7733-B", "Caja seca 53'"),
    Vehiculo("V-03", "NL-1290-C", "Tráiler"),
]
OPERADORES = [Operador("OP-01", "Rigoberto Garza"), Operador("OP-02", "Esteban Mendiola"), Operador("OP-03", "Julián Treviño")]


def sembrar_demo(uow_factory) -> None:
    with uow_factory() as uow:
        for coleccion, repo in ((CLIENTES, uow.clientes), (VEHICULOS, uow.vehiculos), (OPERADORES, uow.operadores)):
            for entidad in coleccion:
                if repo.buscar_por_id(entidad.id) is None:
                    repo.guardar(entidad)
        uow.commit()

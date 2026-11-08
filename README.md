# RutaNorte Logistics — PIA Componentes de Lógica de Negocio

Equipo #2 · Grupo 003 · UANL FIME. Domain Model (DDD) + Service Layer + Repository + Unit of Work + CQRS básico.

## Estructura
```
src/
  domain/          models.py (OrdenServicio, VOs, estados), specifications.py, exceptions.py, repositories.py (puertos)
  application/     services.py (casos de uso), unit_of_work.py (puerto)
  infrastructure/  database.py (DATABASE_URL), orm_models.py, repositories.py, unit_of_work.py, event_bus.py
  api/             main.py (FastAPI + mapeo de errores), routers/, schemas.py, dependencies.py
tests/             unitarias (dominio, specifications) e integración (repositorio, servicio, API)
```
Dependencias: `api → application → domain ← infrastructure`. El dominio no importa FastAPI ni SQLAlchemy.

## Ejecutar
```bash
pip install -r requirements.txt
python -m pytest -v --cov=src --cov-report=term-missing --cov-fail-under=80
uvicorn src.api.main:app --reload        # docs en http://localhost:8000/docs
```
`DATABASE_URL` define la BD (por defecto `sqlite:///rutanorte.db`). Con Docker: `docker compose up app` (PostgreSQL) o `docker compose run tests`.

## Contrato de la API
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/clientes` | Registrar cliente (201) |
| POST | `/orders` | Crear orden en estado inicial REGISTRADO/DRAFT ligada a un cliente (201) |
| GET | `/orders/{id}` | Consultar orden |
| POST | `/orders/{id}/confirmar` · `/asignar-recursos` · `/validar-recoleccion` · `/entregar` · `/cancelar` | CU-01 a CU-05 y cancelación |

Errores: **404** no existe · **409** transición inválida, discrepancia de peso >15% o duplicado · **422** datos inválidos.

## Specifications (`src/domain/specifications.py`)
`ClienteActivoSpecification`, `ClientePreferenteSpecification`, `MontoMinimoSpecification` (>= 1500 MXN), `PromocionActivaSpecification`, componibles con `&`, `|`, `~`.
Regla `beneficio_referencia`: `Preferente & MontoMinimo & ~PromocionActiva`.

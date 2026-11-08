"""Modelos relacionales (tablas). No forman parte del dominio."""
from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Numeric, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ClienteRow(Base):
    __tablename__ = "clientes"

    id = Column(String, primary_key=True)
    razon_social = Column(String, nullable=False)
    es_corporativo = Column(Boolean, nullable=False, default=False)
    es_preferente = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)


class VehiculoRow(Base):
    __tablename__ = "vehiculos"

    id = Column(String, primary_key=True)
    placas = Column(String, nullable=False, index=True)
    tipo_unidad = Column(String, nullable=False)


class OperadorRow(Base):
    __tablename__ = "operadores"

    id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    disponible = Column(Boolean, nullable=False, default=True)


class OrdenRow(Base):
    __tablename__ = "ordenes"

    id = Column(String, primary_key=True)
    cliente_id = Column(String, ForeignKey("clientes.id"), nullable=False)
    vehiculo_id = Column(String, ForeignKey("vehiculos.id"), nullable=True)
    operador_id = Column(String, ForeignKey("operadores.id"), nullable=True)
    origen = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    distancia_km = Column(Float, nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    moneda = Column(String, nullable=False, default="MXN")
    porcentaje_descuento = Column(Float, nullable=False, default=0.0)
    promocion_activa = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False)
    pod_firma_digital = Column(String, nullable=True)
    pod_ine = Column(String, nullable=True)
    pod_fotografias = Column(JSON, nullable=True)

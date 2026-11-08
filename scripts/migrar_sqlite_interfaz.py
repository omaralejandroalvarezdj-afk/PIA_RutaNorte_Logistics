"""Migración no destructiva de BD SQLite creada antes de agregar crédito corporativo.

Usa la base local predeterminada o el archivo pasado como argumento. Crea
respaldo .bak antes de cambiar el esquema. No elimina órdenes ni clientes.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path


def migrar(ruta: Path) -> str:
    if not ruta.is_file():
        return f"No existe {ruta}; no hay base antigua que migrar."
    with sqlite3.connect(ruta) as db:
        tablas = {fila[0] for fila in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "clientes" not in tablas:
            return f"{ruta} no tiene tabla clientes; no se modificó."
        cols = {fila[1] for fila in db.execute("PRAGMA table_info(clientes)")}
        if "dias_morosidad" in cols:
            return f"{ruta} ya tiene dias_morosidad; no se necesitan cambios."
        respaldo = ruta.with_name(ruta.name + ".bak")
        if respaldo.exists():
            raise FileExistsError(f"Ya existe {respaldo}. Guárdalo aparte antes de ejecutar la migración.")
        # Respaldo consistente con el mecanismo de backup de SQLite.
        with sqlite3.connect(respaldo) as destino:
            db.backup(destino)
        db.execute("ALTER TABLE clientes ADD COLUMN dias_morosidad INTEGER NOT NULL DEFAULT 0")
        db.commit()
    return f"Migración completada. Respaldo en: {respaldo}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agregar días de morosidad sin borrar datos existentes")
    parser.add_argument("bd", nargs="?", default="rutanorte.db")
    args = parser.parse_args()
    print(migrar(Path(args.bd)))

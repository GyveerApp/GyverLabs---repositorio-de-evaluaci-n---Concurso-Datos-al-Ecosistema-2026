from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import MovimientoFSE

router = APIRouter()


@router.get("/movimientos")
def listar_movimientos(limite: int = 40, db: Session = Depends(get_db)):
    """Últimos movimientos del Fondo de Servicios Educativos (sintéticos)."""
    movimientos = (
        db.query(MovimientoFSE).order_by(MovimientoFSE.fecha.desc()).limit(limite).all()
    )
    return [
        {
            "fecha": m.fecha.isoformat(),
            "concepto": m.concepto,
            "cuenta_cgn": m.cuenta_cgn,
            "valor": m.valor,
        }
        for m in movimientos
    ]


@router.get("/resumen")
def resumen_fse(db: Session = Depends(get_db)):
    """Totales de ingresos, egresos y saldo — para los KPI del módulo contable."""
    movimientos = db.query(MovimientoFSE).all()
    ingresos = sum(m.valor for m in movimientos if m.valor > 0)
    egresos = sum(-m.valor for m in movimientos if m.valor < 0)
    return {
        "ingresos_totales": round(ingresos, 0),
        "egresos_totales": round(egresos, 0),
        "saldo": round(ingresos - egresos, 0),
        "n_movimientos": len(movimientos),
    }

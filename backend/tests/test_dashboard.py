from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_srd_tablero_estructura():
    r = client.get("/srd/tablero")
    assert r.status_code == 200
    data = r.json()
    assert "total_estudiantes" in data
    assert "mapa_calor" in data
    assert data["total_estudiantes"] > 0


def test_srd_ranking_ordenado_descendente():
    r = client.get("/srd/ranking?limite=10")
    assert r.status_code == 200
    scores = [e["score"] for e in r.json()]
    assert scores == sorted(scores, reverse=True)


def test_fse_resumen():
    r = client.get("/fse/resumen")
    assert r.status_code == 200
    data = r.json()
    assert data["ingresos_totales"] >= 0
    assert data["n_movimientos"] > 0


def test_academico_grados():
    r = client.get("/academico/grados")
    assert r.status_code == 200
    assert len(r.json()) == 5

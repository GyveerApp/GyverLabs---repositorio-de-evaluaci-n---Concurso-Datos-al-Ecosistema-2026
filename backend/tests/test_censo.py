from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_censo_geografia():
    r = client.get("/censo/geografia")
    assert r.status_code == 200
    data = r.json()
    assert "Santander" in data and "Bolívar" in data
    assert "Bucaramanga" in data["Santander"]
    assert "San Pablo" in data["Bolívar"]


def test_censo_resumen_sin_filtro():
    r = client.get("/censo/resumen")
    assert r.status_code == 200
    data = r.json()
    assert data["total_jovenes"] > 0
    assert 0 <= data["pct_fuera_sistema"] <= 100
    assert 0 <= data["pct_zona_riesgo"] <= 100


def test_censo_resumen_filtrado_por_municipio():
    r = client.get("/censo/resumen?departamento=Bolívar&municipio=San Pablo")
    assert r.status_code == 200
    assert r.json()["total_jovenes"] > 0


def test_censo_jovenes_fuera_sistema():
    r = client.get("/censo/jovenes?categoria=fuera_sistema")
    assert r.status_code == 200
    jovenes = r.json()
    assert len(jovenes) > 0
    assert all(j["estudia"] is False for j in jovenes)


def test_censo_jovenes_zona_riesgo():
    r = client.get("/censo/jovenes?categoria=zona_riesgo")
    assert r.status_code == 200
    jovenes = r.json()
    assert len(jovenes) > 0
    assert all(j["zona_riesgo"] is True for j in jovenes)

from fastapi.testclient import TestClient

from app.main import app


def test_logs_are_public(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".log").write_text("diagnostic log\n", encoding="utf-8")
    client = TestClient(app)
    response = client.get("/logs")
    assert response.status_code == 200
    assert response.text == "diagnostic log\n"

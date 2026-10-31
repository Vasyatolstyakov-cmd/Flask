import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    database_path = tmp_path / "test.db"
    database_url = f"sqlite:///{database_path}"
    app = create_app(database_url, testing=True)
    with app.test_client() as test_client:
        yield test_client
    app.extensions["db_engine"].dispose()


def test_advertisement_crud(client):
    create_response = client.post(
        "/advertisements",
        json={
            "title": "Продам велосипед",
            "description": "Городской велосипед в хорошем состоянии",
            "owner": "alexander",
        },
    )
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["id"] == 1
    assert created["title"] == "Продам велосипед"
    assert created["owner"] == "alexander"
    assert created["created_at"].endswith("Z")

    get_response = client.get("/advertisements/1")
    assert get_response.status_code == 200
    assert get_response.get_json() == created

    patch_response = client.patch(
        "/advertisements/1", json={"title": "Велосипед продан"}
    )
    assert patch_response.status_code == 200
    assert patch_response.get_json()["title"] == "Велосипед продан"
    assert (
        patch_response.get_json()["description"]
        == created["description"]
    )

    list_response = client.get("/advertisements")
    assert list_response.status_code == 200
    assert len(list_response.get_json()) == 1

    delete_response = client.delete("/advertisements/1")
    assert delete_response.status_code == 204
    assert client.get("/advertisements/1").status_code == 404


def test_put_replaces_all_editable_fields(client):
    client.post(
        "/advertisements",
        json={
            "title": "Старый",
            "description": "Текст",
            "owner": "owner",
        },
    )

    response = client.put(
        "/advertisements/1",
        json={
            "title": "Новый",
            "description": "Обновлённый текст",
            "owner": "new-owner",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["title"] == "Новый"
    assert response.get_json()["owner"] == "new-owner"


@pytest.mark.parametrize(
    "payload, expected_error",
    [
        ({"title": "Только заголовок"}, "missing fields"),
        (
            {"title": "", "description": "Описание", "owner": "owner"},
            "non-empty string",
        ),
        (
            {
                "title": "Заголовок",
                "description": "Описание",
                "owner": "owner",
                "created_at": "2026-01-01",
            },
            "unknown fields",
        ),
    ],
)
def test_create_validation(client, payload, expected_error):
    response = client.post("/advertisements", json=payload)
    assert response.status_code == 400
    assert expected_error in response.get_json()["error"]


def test_not_found(client):
    assert client.get("/advertisements/999").status_code == 404
    patch_response = client.patch(
        "/advertisements/999",
        json={"title": "Нет"},
    )
    assert patch_response.status_code == 404
    assert client.delete("/advertisements/999").status_code == 404

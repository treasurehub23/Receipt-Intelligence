from fastapi.testclient import TestClient

from app.main import app
from db.database import get_db


def test_patch_missing_expense_returns_404(client):
    response = client.patch(
        "/expenses/999999",
        json={"category": "Groceries"},
    )

    assert response.status_code == 404


def test_patch_updates_category(client, saved_expense):
    response = client.patch(
        f"/expenses/{saved_expense.id}",
        json={"category": "Groceries"},
    )

    assert response.status_code == 200
    assert response.json()["category"] == "Groceries"
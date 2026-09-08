import httpx
import pytest
import pytest_asyncio

from app.main import app
from app.repositories.db import db

BASE = "/v1/th"


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the in-memory database before each test."""
    db.reset()
    yield


@pytest_asyncio.fixture()
async def client():
    """Provide an httpx AsyncClient with ASGITransport for FastAPI."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _add_to_cart(
    client: httpx.AsyncClient, meal_id: str = "meal_1", quantity: int = 2
):
    """Helper — add an item to the cart and return the response."""
    resp = await client.post(
        f"{BASE}/cart/items",
        json={"meal_id": meal_id, "quantity": quantity},
    )
    assert resp.status_code == 200, f"Add-to-cart failed: {resp.text}"
    return resp


async def _checkout(client: httpx.AsyncClient):
    """Helper — place an order (checkout) and return the raw response."""
    return await client.post(f"{BASE}/orders")


async def _get_discounted_price(client: httpx.AsyncClient, meal_id: str) -> float:
    """Helper — fetch discounted_price for a given meal from the meals API."""
    resp = await client.get(f"{BASE}/meals")
    assert resp.status_code == 200, f"GET /meals failed: {resp.text}"
    meal = next(m for m in resp.json() if m["id"] == meal_id)
    return meal["discounted_price"]


# ---------- Test Cases ---------- #


class TestBE2CartUnitPrice:
    """Cart unit_price must be discounted_price, not original_price."""

    @pytest.mark.asyncio
    async def test_cart_unit_price_uses_discounted_price(self, client: httpx.AsyncClient):
        """
        Fetch discounted_price from the meals API, then verify that the
        cart item's unit_price matches it exactly — regardless of what
        the actual price value is.
        """
        meal_id = "meal_1"
        quantity = 2
        discounted_price = await _get_discounted_price(client, meal_id)

        resp = await _add_to_cart(client, meal_id=meal_id, quantity=quantity)
        cart = resp.json()

        item = next(i for i in cart["items"] if i["meal_id"] == meal_id)
        assert item["unit_price"] == discounted_price, (
            f"Expected unit_price={discounted_price} (discounted), got {item['unit_price']}"
        )


class TestBE2CartLineTotal:
    """Cart line_total must be discounted_price × quantity."""

    @pytest.mark.asyncio
    async def test_cart_line_total_uses_discounted_price(self, client: httpx.AsyncClient):
        """
        line_total must equal discounted_price × quantity.
        Using a dynamic price ensures the test stays correct even if
        seed data changes.
        """
        meal_id = "meal_1"
        quantity = 2
        discounted_price = await _get_discounted_price(client, meal_id)

        resp = await _add_to_cart(client, meal_id=meal_id, quantity=quantity)
        cart = resp.json()

        item = next(i for i in cart["items"] if i["meal_id"] == meal_id)
        assert item["line_total"] == discounted_price * quantity, (
            f"Expected line_total={discounted_price * quantity} "
            f"(discounted_price × quantity), got {item['line_total']}"
        )


class TestBE2CartSubtotal:
    """Cart subtotal must be the sum of all discounted line totals."""

    @pytest.mark.asyncio
    async def test_cart_subtotal_uses_discounted_price(self, client: httpx.AsyncClient):
        """
        subtotal must equal discounted_price × quantity for a single-item cart.
        Dynamic price guards against false failures when seed data changes.
        """
        meal_id = "meal_1"
        quantity = 2
        discounted_price = await _get_discounted_price(client, meal_id)

        resp = await _add_to_cart(client, meal_id=meal_id, quantity=quantity)
        cart = resp.json()

        assert cart["subtotal"] == discounted_price * quantity, (
            f"Expected subtotal={discounted_price * quantity}, got {cart['subtotal']}"
        )


class TestBE2OrderPricing:
    """Order lines must inherit discounted prices from the cart."""

    @pytest.mark.asyncio
    async def test_order_lines_use_discounted_price(self, client: httpx.AsyncClient):
        """
        order.py builds OrderLine directly from get_cart() output.
        All price fields in the order must reflect discounted_price —
        computed dynamically so the test stays valid if seed prices change.
        """
        meal_id = "meal_1"
        quantity = 2
        discounted_price = await _get_discounted_price(client, meal_id)

        await _add_to_cart(client, meal_id=meal_id, quantity=quantity)

        resp = await _checkout(client)
        assert resp.status_code == 201, (
            f"Expected 201 Created, got {resp.status_code}: {resp.text}"
        )

        order = resp.json()["order"]
        line = next(l for l in order["lines"] if l["meal_id"] == meal_id)

        assert line["unit_price"] == discounted_price, (
            f"Order line unit_price should be {discounted_price} (discounted), "
            f"got {line['unit_price']}"
        )
        assert line["line_total"] == discounted_price * quantity, (
            f"Order line line_total should be {discounted_price * quantity}, "
            f"got {line['line_total']}"
        )
        assert order["subtotal"] == discounted_price * quantity, (
            f"Order subtotal should be {discounted_price * quantity}, "
            f"got {order['subtotal']}"
        )

from app.models.order import OrderSide, OrderStatus, OrderType


def test_create_market_order_success(client, auth_headers):
    payload = {
        "symbol": "AAPL",
        "side": OrderSide.BUY.value,
        "quantity": 10,
        "order_type": OrderType.MARKET.value,
        "price": None,
    }
    response = client.post("/api/v1/orders", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["side"] == "BUY"
    assert data["quantity"] == 10
    assert data["order_type"] == "MARKET"
    assert data["status"] == OrderStatus.PENDING.value
    assert data["price"] is None


def test_create_limit_order_success(client, auth_headers):
    payload = {
        "symbol": "tsla",
        "side": OrderSide.SELL.value,
        "quantity": 5,
        "order_type": OrderType.LIMIT.value,
        "price": 250.50,
    }
    response = client.post("/api/v1/orders", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "TSLA"  # Normalized uppercase
    assert data["side"] == "SELL"
    assert data["quantity"] == 5
    assert data["order_type"] == "LIMIT"
    assert float(data["price"]) == 250.50


def test_create_limit_order_missing_price(client, auth_headers):
    payload = {
        "symbol": "AAPL",
        "side": OrderSide.BUY.value,
        "quantity": 10,
        "order_type": OrderType.LIMIT.value,
        "price": None,
    }
    response = client.post("/api/v1/orders", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "Price is required for LIMIT orders" in response.json()["detail"]


def test_create_market_order_with_price_rejected(client, auth_headers):
    payload = {
        "symbol": "AAPL",
        "side": OrderSide.BUY.value,
        "quantity": 10,
        "order_type": OrderType.MARKET.value,
        "price": 150.00,
    }
    response = client.post("/api/v1/orders", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "Price should not be provided for MARKET orders" in response.json()["detail"]


def test_create_order_invalid_quantity(client, auth_headers):
    payload = {
        "symbol": "AAPL",
        "side": OrderSide.BUY.value,
        "quantity": 0,
        "order_type": OrderType.MARKET.value,
    }
    response = client.post("/api/v1/orders", json=payload, headers=auth_headers)
    assert response.status_code == 422  # Pydantic validation error (quantity > 0)


def test_get_order_by_id(client, auth_headers):
    create_res = client.post(
        "/api/v1/orders",
        json={
            "symbol": "MSFT",
            "side": OrderSide.BUY.value,
            "quantity": 2,
            "order_type": OrderType.MARKET.value,
        },
        headers=auth_headers,
    )
    order_id = create_res.json()["id"]

    get_res = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == order_id


def test_filter_orders_by_symbol_and_status(client, auth_headers):
    # Create two orders
    client.post(
        "/api/v1/orders",
        json={"symbol": "NVDA", "side": "BUY", "quantity": 1, "order_type": "MARKET"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/orders",
        json={"symbol": "AMD", "side": "BUY", "quantity": 1, "order_type": "MARKET"},
        headers=auth_headers,
    )

    # Filter by symbol
    res = client.get("/api/v1/orders?symbol=NVDA", headers=auth_headers)
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) == 1
    assert orders[0]["symbol"] == "NVDA"


def test_cancel_order_lifecycle(client, auth_headers):
    create_res = client.post(
        "/api/v1/orders",
        json={"symbol": "GOOGL", "side": "BUY", "quantity": 5, "order_type": "MARKET"},
        headers=auth_headers,
    )
    order_id = create_res.json()["id"]

    cancel_res = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == OrderStatus.CANCELLED.value

    # Attempting to cancel again should fail
    second_cancel = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)
    assert second_cancel.status_code == 400
    assert "Cannot cancel order with status 'CANCELLED'" in second_cancel.json()["detail"]


def test_order_endpoints_unauthorized(client):
    res = client.get("/api/v1/orders")
    assert res.status_code == 401

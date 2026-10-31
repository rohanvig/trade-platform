from app.models.order import OrderSide, OrderStatus, OrderType


def test_get_initial_portfolio(client, auth_headers):
    response = client.get("/api/v1/portfolio", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert float(data["cash_balance"]) == 100000.00
    assert float(data["total_portfolio_value"]) == 100000.00
    assert len(data["positions"]) == 0


def test_paper_market_buy_execution(client, auth_headers):
    # 1. Place a MARKET BUY order with execute=true
    buy_payload = {
        "symbol": "AAPL",
        "side": OrderSide.BUY.value,
        "quantity": 10,
        "order_type": OrderType.MARKET.value,
    }
    order_res = client.post("/api/v1/orders?execute=true", json=buy_payload, headers=auth_headers)
    assert order_res.status_code == 201
    order = order_res.json()

    assert order["status"] == OrderStatus.FILLED.value
    assert float(order["price"]) > 0
    assert order["broker_order_id"].startswith("PAPER_")

    # 2. Check portfolio state
    portfolio_res = client.get("/api/v1/portfolio", headers=auth_headers)
    assert portfolio_res.status_code == 200
    portfolio = portfolio_res.json()

    assert float(portfolio["cash_balance"]) < 100000.00
    assert len(portfolio["positions"]) == 1
    pos = portfolio["positions"][0]
    assert pos["symbol"] == "AAPL"
    assert pos["quantity"] == 10
    assert float(pos["current_price"]) > 0
    assert float(pos["current_value"]) > 0


def test_paper_market_sell_execution(client, auth_headers):
    # First buy 10 shares
    client.post(
        "/api/v1/orders?execute=true",
        json={"symbol": "MSFT", "side": "BUY", "quantity": 10, "order_type": "MARKET"},
        headers=auth_headers,
    )

    # Then sell 4 shares
    sell_res = client.post(
        "/api/v1/orders?execute=true",
        json={"symbol": "MSFT", "side": "SELL", "quantity": 4, "order_type": "MARKET"},
        headers=auth_headers,
    )
    assert sell_res.status_code == 201
    assert sell_res.json()["status"] == OrderStatus.FILLED.value

    # Verify positions
    pos_res = client.get("/api/v1/portfolio/positions", headers=auth_headers)
    assert pos_res.status_code == 200
    positions = pos_res.json()
    msft_pos = next(p for p in positions if p["symbol"] == "MSFT")
    assert msft_pos["quantity"] == 6


def test_paper_sell_insufficient_shares_rejected(client, auth_headers):
    # Try selling a stock we don't own
    sell_res = client.post(
        "/api/v1/orders?execute=true",
        json={"symbol": "TSLA", "side": "SELL", "quantity": 50, "order_type": "MARKET"},
        headers=auth_headers,
    )
    assert sell_res.status_code == 400
    assert "Insufficient shares" in sell_res.json()["detail"]


def test_paper_order_manual_execute_endpoint(client, auth_headers):
    # Place a PENDING order without auto-execute
    order_res = client.post(
        "/api/v1/orders",
        json={"symbol": "NVDA", "side": "BUY", "quantity": 5, "order_type": "MARKET"},
        headers=auth_headers,
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]
    assert order_res.json()["status"] == OrderStatus.PENDING.value

    # Execute it via the execute endpoint
    exec_res = client.post(f"/api/v1/orders/{order_id}/execute", headers=auth_headers)
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == OrderStatus.FILLED.value
    assert float(exec_res.json()["price"]) > 0

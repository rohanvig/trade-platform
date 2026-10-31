from decimal import Decimal
import time
from sqlalchemy.orm import Session

from app.models.order import Order, OrderSide, OrderStatus, OrderType
from app.models.portfolio import Position
from app.repositories.portfolio import PortfolioRepository
from app.schemas.portfolio import PortfolioResponse, PositionResponse
from app.services.market import MarketDataService


class PortfolioService:
    """
    Paper Trading & Virtual Portfolio Service.
    Handles virtual cash balances, simulated trade fills against live quotes,
    position tracking with weighted average buy prices, and unrealized PnL.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = PortfolioRepository(db)
        self.market_service = MarketDataService()

    def get_portfolio_summary(self, user_id: int) -> PortfolioResponse:
        portfolio = self.repository.get_or_create_portfolio(user_id)
        positions = self.repository.get_positions(user_id)

        position_responses: list[PositionResponse] = []
        total_invested = Decimal("0.00")
        total_holdings_value = Decimal("0.00")

        for pos in positions:
            # Fetch live quote for current market price
            try:
                quote = self.market_service.get_quote(pos.symbol)
                current_price = Decimal(str(quote.price))
            except Exception:
                # Fallback to purchase price if offline or symbol error
                current_price = pos.average_buy_price

            qty = Decimal(str(pos.quantity))
            current_val = round(qty * current_price, 2)
            invested_val = round(qty * pos.average_buy_price, 2)
            unrealized_pnl = round(current_val - invested_val, 2)
            unrealized_pnl_pct = (
                round((unrealized_pnl / invested_val) * Decimal("100.00"), 2)
                if invested_val > 0
                else Decimal("0.00")
            )

            total_invested += invested_val
            total_holdings_value += current_val

            position_responses.append(
                PositionResponse(
                    symbol=pos.symbol,
                    quantity=pos.quantity,
                    average_buy_price=pos.average_buy_price,
                    current_price=round(current_price, 2),
                    current_value=current_val,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                )
            )

        total_portfolio_value = round(portfolio.cash_balance + total_holdings_value, 2)
        total_unrealized_pnl = round(total_holdings_value - total_invested, 2)
        total_unrealized_pnl_pct = (
            round((total_unrealized_pnl / total_invested) * Decimal("100.00"), 2)
            if total_invested > 0
            else Decimal("0.00")
        )

        return PortfolioResponse(
            user_id=user_id,
            cash_balance=round(portfolio.cash_balance, 2),
            total_invested=round(total_invested, 2),
            total_holdings_value=round(total_holdings_value, 2),
            total_portfolio_value=total_portfolio_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=total_unrealized_pnl_pct,
            positions=position_responses,
        )

    def execute_paper_order(self, order: Order) -> Order:
        """
        Simulate instant paper execution for an order against live market quotes.
        Updates virtual portfolio balance and creates/updates user positions.
        """
        portfolio = self.repository.get_or_create_portfolio(order.user_id)

        try:
            quote = self.market_service.get_quote(order.symbol)
            live_price = Decimal(str(quote.price))
        except Exception as exc:
            # If quote unavailable, reject order
            order.status = OrderStatus.REJECTED
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            raise ValueError(f"Execution failed: Could not fetch market price for '{order.symbol}': {exc}")

        # Check limit order conditions
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and live_price > order.price:
                order.status = OrderStatus.OPEN
                self.db.add(order)
                self.db.commit()
                self.db.refresh(order)
                return order
            elif order.side == OrderSide.SELL and live_price < order.price:
                order.status = OrderStatus.OPEN
                self.db.add(order)
                self.db.commit()
                self.db.refresh(order)
                return order

        exec_price = live_price
        qty = Decimal(str(order.quantity))
        total_trade_amount = round(qty * exec_price, 2)

        if order.side == OrderSide.BUY:
            if portfolio.cash_balance < total_trade_amount:
                order.status = OrderStatus.REJECTED
                self.db.add(order)
                self.db.commit()
                self.db.refresh(order)
                raise ValueError(
                    f"Insufficient funds: Requires ${total_trade_amount}, available cash is ${portfolio.cash_balance}"
                )

            # Deduct cash
            portfolio.cash_balance -= total_trade_amount
            self.repository.update_portfolio(portfolio)

            # Update or create position
            pos = self.repository.get_position_by_symbol(order.user_id, order.symbol)
            if pos is None:
                new_pos = Position(
                    user_id=order.user_id,
                    symbol=order.symbol.upper(),
                    quantity=order.quantity,
                    average_buy_price=round(exec_price, 2),
                )
                self.repository.save_position(new_pos)
            else:
                old_qty = Decimal(str(pos.quantity))
                new_qty = old_qty + qty
                new_avg = ((old_qty * pos.average_buy_price) + total_trade_amount) / new_qty
                pos.quantity = int(new_qty)
                pos.average_buy_price = round(new_avg, 2)
                self.repository.save_position(pos)

        elif order.side == OrderSide.SELL:
            pos = self.repository.get_position_by_symbol(order.user_id, order.symbol)
            if pos is None or pos.quantity < order.quantity:
                available_qty = pos.quantity if pos else 0
                order.status = OrderStatus.REJECTED
                self.db.add(order)
                self.db.commit()
                self.db.refresh(order)
                raise ValueError(
                    f"Insufficient shares: Attempted to sell {order.quantity} of '{order.symbol}', but only {available_qty} available"
                )

            # Credit cash
            portfolio.cash_balance += total_trade_amount
            self.repository.update_portfolio(portfolio)

            # Decrement position
            pos.quantity -= order.quantity
            if pos.quantity == 0:
                self.repository.delete_position(pos)
            else:
                self.repository.save_position(pos)

        # Mark order filled
        order.status = OrderStatus.FILLED
        order.price = round(exec_price, 2)
        order.broker_order_id = f"PAPER_{order.id}_{int(time.time())}"

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

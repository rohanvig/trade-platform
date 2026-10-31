from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order import OrderService


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)

    try:
        return service.create_order(
            user_id=current_user.id,
            order_data=order_data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[OrderResponse],
)
def get_orders(
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    symbol: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)

    return service.get_user_orders(
        user_id=current_user.id,
        status=status_filter,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)

    order = service.get_order(
        order_id=order_id,
        user_id=current_user.id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OrderService(db)

    try:
        return service.cancel_order(
            order_id=order_id,
            user_id=current_user.id,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
"""
Outbox Processor — Transactional Outbox Pattern 实现

从 trade_outbox 表轮询 pending 记录，调用券商 adapter 下单，
完成后原子更新 order 状态 + position + audit_log，标记 outbox 为 done/failed。

设计要点:
- SELECT ... FOR UPDATE SKIP LOCKED 支持多 worker 并发消费
- MAX_RETRIES=3 次重试，超限后回滚 order → rejected
- outbox.order_id 有唯一约束保证幂等
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from workers.trade_executor.adapters.base import OrderRequest, OrderResult
from workers.trade_executor.adapters.registry import get_adapter

logger = logging.getLogger(__name__)

# 配置常量
POLL_INTERVAL_S = 2          # 无待处理记录时的轮询间隔(秒)
BATCH_SIZE = 10              # 每批拉取数量
MAX_RETRIES = 3              # 单条 outbox 最大重试次数
RETRY_BACKOFF_BASE_S = 2     # 重试退避基数 (2^retry_count 秒)

# 状态流转规则 (与原 consumer 一致)
STATUS_TRANSITIONS = {
    "pending": {"submitted", "rejected"},
    "submitted": {"partial_filled", "filled", "cancelled", "rejected"},
    "partial_filled": {"filled", "cancelled", "rejected"},
}


async def run_outbox_processor(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """常驻循环: 轮询 trade_outbox 表，分发 pending 任务到券商。"""
    logger.info("Outbox processor started")

    while True:
        try:
            async with db_session_factory() as session:
                # 拉取一批 pending 记录，FOR UPDATE SKIP LOCKED 避免多 worker 重复消费
                from app.models.trading import TradeOutbox

                stmt = (
                    select(TradeOutbox)
                    .where(TradeOutbox.status == "pending")
                    .order_by(TradeOutbox.created_at)
                    .limit(BATCH_SIZE)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                batch = result.scalars().all()

            if not batch:
                await asyncio.sleep(POLL_INTERVAL_S)
                continue

            # 逐条处理（每条独立事务）
            for outbox in batch:
                await _dispatch_one(db_session_factory, outbox.id)

        except Exception:
            logger.exception("Outbox processor loop error, will retry")
            await asyncio.sleep(POLL_INTERVAL_S)


async def _dispatch_one(
    db_session_factory: async_sessionmaker[AsyncSession],
    outbox_id: int,
) -> None:
    """处理单条 outbox 记录: 调用券商 → 更新 DB → 标记 outbox。"""
    async with db_session_factory() as session:
        from app.models.trading import TradeOutbox, Order, BrokerAccount, Position, AuditLog

        # 重新加载最新状态 (可能已被其他 worker 取走)
        stmt = select(TradeOutbox).where(TradeOutbox.id == outbox_id)
        result = await session.execute(stmt)
        outbox = result.scalar_one_or_none()

        if outbox is None or outbox.status != "pending":
            return

        # 加载关联的 Order + BrokerAccount
        order_stmt = select(Order).where(Order.id == outbox.order_id).with_for_update()
        order_result = await session.execute(order_stmt)
        order = order_result.scalar_one_or_none()

        if order is None:
            logger.error(f"Outbox {outbox_id}: order {outbox.order_id} not found, marking skipped")
            outbox.status = "skipped"
            outbox.last_error = f"Order {outbox.order_id} not found"
            outbox.processed_at = datetime.now(timezone.utc)
            await session.commit()
            return

        acct_stmt = select(BrokerAccount).where(
            BrokerAccount.id == order.broker_account_id
        ).with_for_update()
        acct_result = await session.execute(acct_stmt)
        account = acct_result.scalar_one_or_none()

        if account is None:
            logger.error(f"Outbox {outbox_id}: broker_account {order.broker_account_id} not found")
            outbox.status = "failed"
            outbox.last_error = "BrokerAccount not found"
            outbox.processed_at = datetime.now(timezone.utc)
            order.status = "rejected"
            await session.commit()
            return

        # ── 调用券商 Adapter ──
        try:
            adapter = get_adapter(
                account.broker_type,
                db_session_factory=db_session_factory,
                broker_account_id=account.id,
            )
            adapter.connect({})

            req_json = outbox.request_json
            execution_price = (
                Decimal(str(req_json["price"])) if req_json.get("price") else None
            )
            if execution_price is None:
                from app.models.market import Klines

                price_result = await session.execute(
                    select(Klines.close)
                    .where(Klines.symbol == order.symbol)
                    .order_by(Klines.ts.desc())
                    .limit(1)
                )
                market_price = price_result.scalar_one_or_none()
                if market_price is not None:
                    slippage = account.slippage_rate or Decimal("0")
                    direction = Decimal("1") if order.side == "buy" else Decimal("-1")
                    execution_price = market_price * (Decimal("1") + direction * slippage)

            request = OrderRequest(
                symbol=req_json["symbol"],
                side=req_json["side"],
                order_type=req_json["order_type"],
                price=execution_price,
                volume=Decimal(str(req_json["volume"])),
            )

            pos_stmt = select(Position).where(
                Position.broker_account_id == order.broker_account_id,
                Position.symbol == order.symbol,
            ).with_for_update()
            pos_result = await session.execute(pos_stmt)
            pos = pos_result.scalar_one_or_none()

            estimated_gross = (
                execution_price * order.volume
                if execution_price is not None
                else Decimal("0")
            )
            estimated_commission = max(
                estimated_gross * account.commission_rate,
                account.minimum_commission,
            ).quantize(Decimal("0.01"))

            if execution_price is None:
                broker_result = OrderResult(
                    broker_order_id=f"MOCK-REJECTED-{order.id}",
                    status="rejected",
                    message="No market price available",
                )
            elif (
                account.broker_type == "mock"
                and order.side == "sell"
                and (pos is None or pos.volume < order.volume)
            ):
                broker_result = OrderResult(
                    broker_order_id=f"MOCK-REJECTED-{order.id}",
                    status="rejected",
                    message="Insufficient position",
                )
            elif (
                account.broker_type == "mock"
                and order.side == "buy"
                and account.cash_balance < estimated_gross + estimated_commission
            ):
                broker_result = OrderResult(
                    broker_order_id=f"MOCK-REJECTED-{order.id}",
                    status="rejected",
                    message="Insufficient cash",
                )
            else:
                broker_result = adapter.place_order(request)

            # 状态流转校验
            allowed_next = STATUS_TRANSITIONS.get(order.status, set())
            if broker_result.status not in allowed_next:
                raise ValueError(
                    f"Illegal status transition: {order.status} → {broker_result.status}"
                )

            # ── 更新 Order ──
            now = datetime.now(timezone.utc)
            order.status = broker_result.status
            order.broker_order_id = broker_result.broker_order_id
            order.updated_at = now

            previous_filled = order.filled_volume or Decimal("0")
            filled = broker_result.filled_volume
            filled_delta = Decimal("0")
            if filled is not None and filled > 0:
                filled_delta = min(filled, order.volume - previous_filled)
            elif broker_result.status == "filled":
                filled_delta = order.volume - previous_filled
            order.filled_volume = previous_filled + filled_delta

            fill_gross = (execution_price or Decimal("0")) * filled_delta
            fill_commission = Decimal("0")
            fill_stamp_duty = Decimal("0")
            if filled_delta > 0:
                fill_commission = max(
                    fill_gross * account.commission_rate,
                    account.minimum_commission,
                ).quantize(Decimal("0.01"))
                if order.side == "sell":
                    fill_stamp_duty = (
                        fill_gross * account.stamp_duty_rate
                    ).quantize(Decimal("0.01"))
                order.filled_price = execution_price
                order.commission += fill_commission
                order.stamp_duty += fill_stamp_duty

            # ── 更新 Position ──
            if broker_result.status in ("filled", "partial_filled") and filled_delta > 0:
                if order.side == "buy":
                    if pos:
                        total_cost = (
                            pos.avg_cost * pos.volume
                            + (execution_price or 0) * filled_delta
                            + fill_commission
                        )
                        pos.volume += filled_delta
                        pos.avg_cost = total_cost / pos.volume
                    else:
                        pos = Position(
                            broker_account_id=order.broker_account_id,
                            symbol=order.symbol,
                            volume=filled_delta,
                            avg_cost=(fill_gross + fill_commission) / filled_delta,
                        )
                        session.add(pos)
                elif order.side == "sell" and pos is not None:
                    pos.volume -= filled_delta

                if account.broker_type == "mock":
                    if order.side == "buy":
                        account.cash_balance -= fill_gross + fill_commission
                    else:
                        account.cash_balance += (
                            fill_gross - fill_commission - fill_stamp_duty
                        )

                if pos is not None:
                    pos.updated_at = now
                    if pos.volume == 0:
                        await session.delete(pos)

            # ── 写审计日志 ──
            audit = AuditLog(
                user_id=order.user_id,
                action="order_create",
                actor_type=order.origin,
                target_type="order",
                target_id=order.id,
                detail={
                    "symbol": order.symbol,
                    "side": order.side,
                    "price": float(order.price) if order.price else None,
                    "volume": float(order.volume),
                    "result_status": broker_result.status,
                    "broker_order_id": broker_result.broker_order_id,
                    "filled_price": float(order.filled_price) if order.filled_price else None,
                    "commission": float(order.commission),
                    "stamp_duty": float(order.stamp_duty),
                    "via_outbox": True,
                    "outbox_id": outbox_id,
                },
            )
            session.add(audit)

            # 标记 outbox 完成
            outbox.status = "done"
            outbox.processed_at = now
            outbox.last_error = None

            await session.commit()
            logger.info(
                f"Outbox {outbox_id} done: order {order.client_order_id} → {broker_result.status}"
            )

            adapter.disconnect()

        except Exception as exc:
            outbox.retry_count += 1
            outbox.last_error = str(exc)

            if outbox.retry_count >= MAX_RETRIES:
                # 超过重试上限: 回滚订单为 rejected
                outbox.status = "failed"
                outbox.processed_at = datetime.now(timezone.utc)
                order.status = "rejected"
                order.updated_at = datetime.now(timezone.utc)

                # 失败审计日志
                fail_audit = AuditLog(
                    user_id=order.user_id,
                    action="order_failed",
                    actor_type="system",
                    target_type="order",
                    target_id=order.id,
                    detail={
                        "reason": str(exc),
                        "retry_count": outbox.retry_count,
                        "outbox_id": outbox_id,
                    },
                )
                session.add(fail_audit)
                await session.commit()
                logger.error(
                    f"Outbox {outbox_id} FAILED after {MAX_RETRIES} retries: "
                    f"order {order.client_order_id} rolled back to rejected"
                )
            else:
                # 还可重试: 保持 pending，下次轮询继续
                await session.commit()
                backoff = RETRY_BACKOFF_BASE_S ** outbox.retry_count
                logger.warning(
                    f"Outbox {outbox_id} attempt {outbox.retry_count}/{MAX_RETRIES} failed: "
                    f"{exc}, retrying in {backoff}s"
                )
                await asyncio.sleep(backoff)

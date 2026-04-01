import uuid
from datetime import datetime, timezone

from app.models.market import (
    AlertRule,
    CreateAlertRuleRequest,
    AlertHistoryItem,
    CreateAlertHistoryRequest,
)
from app.repositories.alert_repository import AlertRepository
from app.repositories.ticker_repository import TickerRepository


class AlertService:
    def __init__(self, repository: AlertRepository, ticker_repository: TickerRepository) -> None:
        self.repository = repository
        self.ticker_repository = ticker_repository

    def list_alerts(self) -> list[AlertRule]:
        active_codes = {ticker.code for ticker in self.ticker_repository.list_all()}
        return [alert for alert in self.repository.list_all() if alert.market in active_codes]

    def add_alert(self, request: CreateAlertRuleRequest) -> list[AlertRule]:
        market = request.market.strip().upper()
        direction = request.direction.strip().lower()
        if direction not in {"above", "below"}:
            raise ValueError("Alert direction must be 'above' or 'below'.")

        active_codes = {ticker.code for ticker in self.ticker_repository.list_all()}
        if market not in active_codes:
            raise ValueError(f"Ticker code '{market}' was not found.")

        alert = AlertRule(
            id=str(uuid.uuid4()),
            market=market,
            direction=direction,
            value=request.value,
            enabled=True,
            metadata=request.metadata,
        )
        return self.repository.add(alert)

    def delete_alert(self, alert_id: str) -> list[AlertRule]:
        return self.repository.delete(alert_id)

    def record_history(self, request: CreateAlertHistoryRequest) -> AlertHistoryItem:
        market = request.market.strip().upper()
        direction = request.direction.strip().lower()
        if direction not in {"above", "below"}:
            raise ValueError("Alert direction must be 'above' or 'below'.")

        active_codes = {ticker.code for ticker in self.ticker_repository.list_all()}
        if market not in active_codes:
            raise ValueError(f"Ticker code '{market}' was not found.")

        if request.alert_rule_id:
            alert = self.repository.get(request.alert_rule_id)
            if alert is None:
                raise ValueError(f"Alert '{request.alert_rule_id}' was not found.")
            if (
                alert.market != market
                or alert.direction != direction
                or abs(alert.value - request.threshold) > 1e-9
            ):
                raise ValueError("Alert history payload does not match the referenced alert rule.")

        id = str(uuid.uuid4())
        self.repository.record_history(
            id=id,
            alert_rule_id=request.alert_rule_id,
            market=market,
            direction=direction,
            threshold=request.threshold,
            price=request.price,
        )
        return AlertHistoryItem(
            id=id,
            alert_rule_id=request.alert_rule_id,
            market=market,
            direction=direction,
            threshold=request.threshold,
            price=request.price,
            triggered_at=datetime.now(timezone.utc),
        )

    def list_history(self, limit: int = 50) -> list[AlertHistoryItem]:
        rows = self.repository.list_history(limit=limit)
        return [
            AlertHistoryItem(
                id=row["id"],
                alert_rule_id=row["alert_rule_id"],
                market=row["market"],
                direction=row["direction"],
                threshold=row["threshold"],
                price=row["price"],
                triggered_at=row["triggered_at"],
            )
            for row in rows
        ]

import uuid

from app.models.market import AlertRule, CreateAlertRuleRequest
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

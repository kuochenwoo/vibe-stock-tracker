from app.models.market import AlertHistoryReadPreference, PanelOrderPreference
from app.repositories.preferences_repository import PreferencesRepository
from app.repositories.ticker_repository import TickerRepository


class PreferencesService:
    def __init__(
        self,
        repository: PreferencesRepository,
        ticker_repository: TickerRepository,
    ) -> None:
        self.repository = repository
        self.ticker_repository = ticker_repository

    def get_panel_order(self) -> PanelOrderPreference:
        preference = self.repository.get_panel_order()
        return self._sanitize_panel_order(preference.codes, preference.updated_at)

    def save_panel_order(self, codes: list[str]) -> PanelOrderPreference:
        sanitized = self._sanitize_codes_only(codes)
        return self.repository.save_panel_order(sanitized)

    def get_alert_history_read(self) -> AlertHistoryReadPreference:
        return self.repository.get_alert_history_read()

    def save_alert_history_read(self, last_read_triggered_at) -> AlertHistoryReadPreference:
        return self.repository.save_alert_history_read(last_read_triggered_at)

    def _sanitize_panel_order(self, codes: list[str], updated_at) -> PanelOrderPreference:
        return PanelOrderPreference(
            codes=self._sanitize_codes_only(codes),
            updated_at=updated_at,
        )

    def _sanitize_codes_only(self, codes: list[str]) -> list[str]:
        active_codes = {ticker.code for ticker in self.ticker_repository.list_all()}
        seen: set[str] = set()
        normalized: list[str] = []

        for code in codes:
            normalized_code = code.strip().upper()
            if not normalized_code or normalized_code in seen or normalized_code not in active_codes:
                continue
            seen.add(normalized_code)
            normalized.append(normalized_code)

        for code in sorted(active_codes):
            if code not in seen:
                normalized.append(code)

        return normalized

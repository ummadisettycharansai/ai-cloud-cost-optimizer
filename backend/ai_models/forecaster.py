"""
Enhanced Cost Forecaster — Production FinOps Edition

Improvements over v1:
  - Includes confidence intervals (yhat_lower / yhat_upper) as forecast_low / forecast_high
  - Returns eom_projected_spend in the summary
  - Linear fallback when Prophet is not installed
"""
import datetime
import logging
from typing import Any, List, Dict, Optional

import pandas as pd  # pyre-ignore[21]

try:
    from prophet import Prophet  # pyre-ignore[21]
    PROPHET_AVAILABLE = True
except ImportError:
    Prophet = None
    PROPHET_AVAILABLE = False

logger = logging.getLogger(__name__)


def _days_remaining_in_month() -> int:
    import calendar
    today = datetime.date.today()
    total = calendar.monthrange(today.year, today.month)[1]
    return total - today.day


def _linear_forecast(history_data: List[Dict[str, Any]], forecast_days: int) -> List[Dict[str, Any]]:
    """
    Simple linear trend extrapolation as a Prophet fallback.
    Uses first and last data point to compute slope.
    """
    if len(history_data) < 2:
        return []

    costs = [float(d['cost']) for d in history_data]
    n = len(costs)
    slope = (costs[-1] - costs[0]) / max(n - 1, 1)

    last_cost = costs[-1]
    last_date = datetime.date.fromisoformat(str(history_data[-1]['date']))

    forecast = []
    for i in range(1, forecast_days + 1):
        future_date = last_date + datetime.timedelta(days=i)
        predicted = max(0.0, last_cost + slope * i)
        # Add simple ±10% confidence band for the fallback
        forecast.append({
            "date": str(future_date),
            "forecast_cost": round(predicted, 2),
            "forecast_low": round(predicted * 0.90, 2),
            "forecast_high": round(predicted * 1.10, 2),
        })

    return forecast


class CostForecaster:
    def __init__(self):
        self.model: Any = None

    def forecast_costs(
        self,
        history_data: List[Dict[str, Any]],
        forecast_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Returns a structured response:
        {
            "forecast": [...],           # list of {date, forecast_cost, forecast_low, forecast_high}
            "eom_projected_spend": float, # estimated total spend by end of current month
            "model_used": "prophet" | "linear"
        }
        """
        if not history_data or len(history_data) < 2:
            return {"forecast": [], "eom_projected_spend": 0.0, "model_used": "none"}

        if not PROPHET_AVAILABLE:
            logger.warning("Prophet not installed — using linear fallback.")
            forecast = _linear_forecast(history_data, forecast_days)
            eom = self._compute_eom(history_data, forecast)
            return {"forecast": forecast, "eom_projected_spend": eom, "model_used": "linear"}

        try:
            df = pd.DataFrame(history_data)
            df['ds'] = pd.to_datetime(df['date'])
            df['y'] = df['cost'].astype(float)
            df = df[['ds', 'y']].sort_values(by='ds').drop_duplicates('ds')

            self.model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=False,
                interval_width=0.80,   # 80% confidence interval
            )
            self.model.fit(df)

            future = self.model.make_future_dataframe(periods=forecast_days)
            forecast_df = self.model.predict(future)

            last_history_date = df['ds'].max()
            future_only = forecast_df[forecast_df['ds'] > last_history_date]

            forecast = []
            for _, row in future_only.iterrows():
                forecast.append({
                    "date": row['ds'].strftime("%Y-%m-%d"),
                    "forecast_cost": round(max(0.0, float(row['yhat'])), 2),  # pyre-ignore[6]
                    "forecast_low": round(max(0.0, float(row['yhat_lower'])), 2),  # pyre-ignore[6]
                    "forecast_high": round(max(0.0, float(row['yhat_upper'])), 2),  # pyre-ignore[6]
                })

            eom = self._compute_eom(history_data, forecast)
            return {"forecast": forecast, "eom_projected_spend": eom, "model_used": "prophet"}

        except Exception as exc:
            logger.error(f"Prophet forecast failed: {exc}. Falling back to linear.")
            forecast = _linear_forecast(history_data, forecast_days)
            eom = self._compute_eom(history_data, forecast)
            return {"forecast": forecast, "eom_projected_spend": eom, "model_used": "linear"}

    def _compute_eom(
        self,
        history_data: List[Dict[str, Any]],
        forecast: List[Dict[str, Any]],
    ) -> float:
        """
        Estimated end-of-month total: current month actuals + forecasted remaining days.
        """
        import calendar
        today = datetime.date.today()
        month_start = today.replace(day=1)

        # Sum actual spend this month from history
        actual_this_month = sum(
            float(d['cost'])
            for d in history_data
            if datetime.date.fromisoformat(str(d['date'])) >= month_start
        )

        # Sum forecasted remaining days in the current month
        eom_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        forecast_remaining = sum(
            float(f['forecast_cost'])
            for f in forecast
            if datetime.date.fromisoformat(f['date']) <= eom_day
        )

        return round(actual_this_month + forecast_remaining, 2)

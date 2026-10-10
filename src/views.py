import json
import os
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

import requests

BASE_DIR = Path(__file__).resolve().parent
USER_SETTINGS_PATH = BASE_DIR / "../user_settings.json"

load_dotenv()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")


def load_user_settings():
    with open(USER_SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_month_range(input_date: date):
    """Возвращает диапазон дат: от 1-го числа месяца до input_date включительно."""
    start_date = input_date.replace(day=1)
    return start_date, input_date


def fetch_currency_rates(base_currency: str, currencies: list, start_date: date, end_date: date):
    """
    Получает курсы валют через Alpha Vantage (Time Series Daily).
    Возвращает список записей {date, base, target, rate} за указанный период.
    """
    url = "https://www.alphavantage.co/query"
    data_all = []

    for target in currencies:
        if target == base_currency:
            continue
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": f"{base_currency}{target}",
            "apikey": ALPHA_VANTAGE_API_KEY,
            "outputsize": "full"
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        time_series = data.get("Time Series (Daily)", {})
        for d_str, values in time_series.items():
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
            if start_date <= d <= end_date:
                rate = float(values["4. close"])
                data_all.append({
                    "date": d_str,
                    "base": base_currency,
                    "target": target,
                    "rate": rate
                })
    return data_all


def fetch_stock_prices(symbols: list, start_date: date, end_date: date):
    """
    Получает цены акций через Finnhub (Stock Candles, дневной интервал).
    Возвращает список записей {date, symbol, open, high, low, close, volume}.
    """
    url = "https://finnhub.io/api/v1/stock/candle"
    data_all = []

    for symbol in symbols:
        params = {
            "symbol": symbol,
            "resolution": "D",
            "from": int(datetime.combine(start_date, datetime.min.time()).timestamp()),
            "to": int(datetime.combine(end_date, datetime.max.time()).timestamp()),
            "token": FINNHUB_API_KEY
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("s") != "ok":
            continue

        for i, t in enumerate(data["t"]):
            d = datetime.fromtimestamp(t).date()
            if start_date <= d <= end_date:
                data_all.append({
                    "date": d.isoformat(),
                    "symbol": symbol,
                    "open": data["o"][i],
                    "high": data["h"][i],
                    "low": data["l"][i],
                    "close": data["c"][i],
                    "volume": data["v"][i]
                })
    return data_all


def generate_json_response(input_date_str: str):
    """
    Главная функция: формирует JSON-ответ с данными за период
    с начала месяца по input_date_str.
    Формат input_date_str: 'DD.MM.YYYY'
    """
    # Парсинг даты
    input_date = datetime.strptime(input_date_str, "%d.%m.%Y").date()
    start_date, end_date = get_month_range(input_date)

    # Загрузка пользовательских настроек
    settings = load_user_settings()
    user_currencies = settings["user_currencies"]
    user_stocks = settings["user_stocks"]

    # Получение данных
    currency_data = fetch_currency_rates(
        base_currency="USD",  # базовая валюта для конвертации
        currencies=user_currencies,
        start_date=start_date,
        end_date=end_date
    )
    stock_data = fetch_stock_prices(
        symbols=user_stocks,
        start_date=start_date,
        end_date=end_date
    )

    # Формирование ответа
    response = {
        "request_date": input_date_str,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "currencies": currency_data,
        "stocks": stock_data
    }
    return response


if __name__ == "__main__":
    result = generate_json_response("20.05.2020")
    print(json.dumps(result, ensure_ascii=False, indent=2))
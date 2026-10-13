import datetime
import json
import logging
from bisect import bisect
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import requests

from settings import STORAGE_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def greet() -> str:
    """Функция приветствия, связанная со временем суток."""
    hour = datetime.datetime.now().hour

    boundaries = [0, 6, 12, 18]
    greetings = [
        "Доброй ночи",
        "Доброе утро",
        "Добрый день",
        "Добрый вечер",
    ]

    return greetings[bisect(boundaries, hour) - 1]


def read_xlsx(path: str | Path) -> pd.DataFrame:
    """Чтение Excel-файла. Если не найден — выбрасывает FileNotFoundError."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    return pd.read_excel(path)


def process_data(date_start: datetime.datetime, date_end: datetime.datetime) -> pd.DataFrame:
    """
    Читает файл операций, парсит даты и фильтрует по диапазону.
    Путь к файлу строится относительно STORAGE_PATH.
    """
    file_path = (Path(STORAGE_PATH) / "../data/operations.xlsx").resolve()
    data = read_xlsx(file_path)

    # Парсим дату в нужном формате
    data["Дата операции"] = pd.to_datetime(
        data["Дата операции"],
        format="%d.%m.%Y %H:%M:%S",
        errors="raise",
    )

    return data.query("`Дата операции` > @date_start and `Дата операции` < @date_end")


def process_cards(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Считает расходы и кешбэк по картам (последние 4 цифры)."""
    expenses = df[df["Сумма операции"] < 0].copy()

    # Извлекаем последние 4 цифры из номера карты
    expenses["last_digits"] = (
        expenses["Номер карты"]
        .astype(str)
        .str.replace("*", "", regex=False)
        .str[-4:]
    )

    grouped = expenses.groupby("last_digits")["Сумма операции"].sum()
    result = []
    for last_digits, total_spent_raw in grouped.items():
        total_spent = abs(total_spent_raw)
        cashback = round(total_spent / 100, 2)
        result.append({
            "last_digits": last_digits,
            "total_spent": round(total_spent, 2),
            "cashback": cashback,
        })
    return result


def get_top_transactions(df: pd.DataFrame, top_n: int = 5) -> List[Dict[str, Any]]:
    """Топ-N транзакций по модулю суммы."""
    # Сортируем по абсолютной величине суммы
    sorted_df = df.sort_values(by="Сумма операции", key=lambda x: x.abs(), ascending=False).head(top_n)

    result = []
    for _, row in sorted_df.iterrows():
        op_date = row["Дата операции"].strftime("%d.%m.%Y")
        result.append({
            "date": op_date,
            "amount": round(abs(row["Сумма операции"]), 2),
            "category": row["Категория"],
            "description": row.get("Описание", ""),
        })
    return result


def fetch_currency_rates() -> List[Dict[str, Any]]:
    """Получает курсы USD и EUR. При ошибке — возвращает заглушки."""
    try:
        response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js", timeout=5)
        response.raise_for_status()
        data = response.json()
        rates = data["Valute"]
        result = []
        for code in ["USD", "EUR"]:
            info = rates.get(code)
            if info:
                result.append({
                    "currency": code,
                    "rate": round(info["Value"], 2),
                })
        return result
    except Exception as e:
        logger.warning(f"Не удалось получить курсы валют: {e}")
        return [
            {"currency": "USD", "rate": 73.21},
            {"currency": "EUR", "rate": 87.08},
        ]


def fetch_stock_prices() -> List[Dict[str, Any]]:
    """Заглушка для цен акций S&P500. В реальном проекте — запрос к биржевому API."""
    return [
        {"stock": "AAPL", "price": 150.12},
        {"stock": "AMZN", "price": 3173.18},
        {"stock": "GOOGL", "price": 2742.39},
        {"stock": "MSFT", "price": 296.71},
        {"stock": "TSLA", "price": 1007.08},
    ]


def generate_report(input_date_str: str) -> str:
    """
    Главная функция: принимает дату в формате YYYY-MM-DD HH:MM:SS,
    возвращает JSON-отчёт.

    Логика:
      - берём переданное время как «текущее» для приветствия;
      - для выборки данных берём небольшой диапазон вокруг этой даты
        (например, ±1 день), чтобы в выборке были транзакции.
    """
    try:
        dt = datetime.datetime.strptime(input_date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        logger.error(f"Неверный формат даты: {e}")
        raise ValueError("Дата должна быть в формате YYYY-MM-DD HH:MM:SS")


    def greet_at(t: datetime.datetime) -> str:
        hour = t.hour
        boundaries = [0, 6, 12, 18]
        greetings = ["Доброй ночи", "Доброе утро", "Добрый день", "Добрый вечер"]
        return greetings[bisect(boundaries, hour) - 1]

    greeting = greet_at(dt)

    date_start = dt - datetime.timedelta(days=1)
    date_end = dt + datetime.timedelta(days=1)

    df = process_data(date_start, date_end)

    cards_data = process_cards(df)
    top_trans = get_top_transactions(df, top_n=5)
    rates = fetch_currency_rates()
    stocks = fetch_stock_prices()

    report = {
        "greeting": greeting,
        "cards": cards_data,
        "top_transactions": top_trans,
        "currency_rates": rates,
        "stock_prices": stocks,
    }

    return json.dumps(report, ensure_ascii=False, indent=2)


# Пример использования (раскомментируй для теста)
if __name__ == "__main__":
    result_json = generate_report("2021-12-31 14:30:00")
    print(result_json)

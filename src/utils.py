import datetime
from bisect import bisect
from pathlib import Path

import pandas as pd
from pandas import to_datetime

from settings import DATETIME_FORMAT_DMY_HMS, STORAGE_PATH


def greet() -> str:
    """Функция приветствия связаная со временем суток"""
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
    """Функция чтения эксель файла, если не найден вернется обработка ошибки"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    return pd.read_excel(path)


def process_data(date_start: datetime.datetime, date_end: datetime.datetime) -> pd.DataFrame:
    """Функция чтения даты и преобразования в нужный формат"""
    file_path = Path(STORAGE_PATH) / "operations.xlsx"
    data = read_xlsx(file_path)

    data["Дата операции"] = to_datetime(
        data["Дата операции"],
        format="%d.%m.%Y %H:%M:%S",
        errors="raise",
    )

    return data.query("`Дата операции` > @date_start and `Дата операции` < @date_end")


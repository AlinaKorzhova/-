import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Callable, Any, ParamSpec, TypeVar

import pandas as pd

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def write_to_file(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Декоратор для записи результата работы функции в текстовый файл.
    """

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = function(*args, **kwargs)

            with open("result.txt", "a", encoding='utf-8') as file:
                file.write(f"{name}: {result}\n")

            return result

        return wrapper

    return decorator


def report_logger(filename: Optional[str] = None):
    """
    Декоратор для функций-отчетов.
    Без параметров: пишет в файл по умолчанию (report_YYYY-MM-DD_HH-MM-SS.json).
    С параметром: пишет в указанный файл.

    Записывает в файл JSON результат, который возвращает декорируемая функция.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            # Определение имени файла
            if filename is None:
                default_name = f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
                file_path = default_name
            else:
                file_path = filename

            # Сериализация результата в JSON
            # Если результат DataFrame, конвертируем в dict (orient='records')
            if isinstance(result, pd.DataFrame):
                data_to_save = result.to_dict(orient='records')
            elif isinstance(result, pd.Series):
                data_to_save = result.to_dict()
            else:
                data_to_save = result

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=4)
                logger.info(f"Отчет успешно сохранен в файл: {file_path}")
            except Exception as e:
                logger.error(f"Ошибка при записи отчета в файл {file_path}: {e}")
                raise

            return result

        return wrapper

    return decorator


@report_logger()
@write_to_file("spending_by_category_report")
def spending_by_category(transactions: pd.DataFrame,
                         category: str,
                         date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает траты по заданной категории за последние три месяца.

    Параметры:
        transactions: pd.DataFrame с транзакциями (должна содержать колонки: 
                      'Дата операции', 'Категория', 'Сумма операции').
        category: Название категории для фильтрации.
        date: Строка даты в формате 'DD.MM.YYYY'. Если не передана, берется текущая дата.

    Возвращает:
        pd.DataFrame с отфильтрованными транзакциями.
    """
    # Копирование, чтобы не менять исходный DataFrame
    df = transactions.copy()

    # Приведение колонки даты к datetime
    # Предполагаем, что в Excel дата может быть строкой или уже datetime
    if not pd.api.types.is_datetime64_any_dtype(df['Дата операции']):
        df['Дата операции'] = pd.to_datetime(df['Дата операции'], format='%d.%m.%Y %H:%M:%S', errors='coerce')

    # Определение опорной даты
    if date is None:
        ref_date = datetime.now()
    else:
        try:
            ref_date = datetime.strptime(date, '%d.%m.%Y')
        except ValueError:
            logger.error("Неверный формат даты. Используйте DD.MM.YYYY")
            raise

    # Расчет даты начала периода (3 месяца назад)
    # Простая эвристика: вычитаем 90 дней для универсальности
    start_date = ref_date - timedelta(days=90)

    # Фильтрация по категории (регистронезависимо)
    mask_category = df['Категория'].str.lower() == category.lower()

    # Фильтрация по дате
    mask_date = (df['Дата операции'] >= start_date) & (df['Дата операции'] <= ref_date)

    # Фильтрация только расходов (отрицательные суммы)
    mask_amount = df['Сумма операции'] < 0

    filtered_df = df[mask_category & mask_date & mask_amount].copy()

    if filtered_df.empty:
        logger.info(f"Транзакций по категории '{category}' за последние 3 месяца не найдено.")
        return pd.DataFrame()

    # Сортировка по дате (новые сначала)
    filtered_df = filtered_df.sort_values(by='Дата операции', ascending=False)

    return filtered_df

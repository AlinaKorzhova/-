import json
import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

DEFAULT_CASHBACK_RATE = 0.05
DATE_FORMAT_EXCEL = "%d.%m.%Y %H:%M:%S"


def _parse_excel_date(date_str):
    """Парсит дату из формата Excel (31.12.2021 16:44:00)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), DATE_FORMAT_EXCEL)
    except ValueError:
        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None


def _is_valid_transaction(transaction, year, month):
    """Предикат для фильтрации: расходы за нужный месяц, исключая переводы и пополнения."""
    date = _parse_excel_date(transaction.get("Дата операции"))
    if not date or date.year != year or date.month != month:
        return False

    amount = transaction.get("Сумма операции", 0)
    # В Excel расходы обычно отрицательные
    if amount >= 0:
        return False

    category = transaction.get("Категория", "")
    if category in ["Переводы", "Пополнения"]:
        return False

    return True


def _extract_cashback_data(transaction):
    """Map-функция: превращает транзакцию в пару (Категория, Кешбэк)."""
    category = transaction.get("Категория", "Прочие")
    amount = abs(float(transaction.get("Сумма операции", 0)))
    cashback = amount * DEFAULT_CASHBACK_RATE
    return category, cashback


def analyze_cashback_categories(data, year, month):
    """
    Анализирует выгодные категории кешбэка.
    Вместо reduce используется defaultdict для накопления сумм.
    """
    logger.info(f"Запуск анализа кешбэка за {month}.{year}")

    # 1. Фильтрация (Functional: filter)
    filtered_transactions = filter(
        lambda t: _is_valid_transaction(t, year, month),
        data
    )

    # 2. Преобразование (Functional: map)
    cashback_pairs = map(_extract_cashback_data, filtered_transactions)

    # 3. Агрегация (Императивный стиль вместо reduce)
    # defaultdict автоматически создает ключ со значением 0, если его нет
    result_dict = defaultdict(float)

    for category, value in cashback_pairs:
        result_dict[category] += value

    # Приводим к обычному dict и округляем
    final_result = {k: round(v, 2) for k, v in result_dict.items()}

    logger.info(f"Анализ завершен. Найдено категорий: {len(final_result)}")
    return json.dumps(final_result, ensure_ascii=False, indent=4)

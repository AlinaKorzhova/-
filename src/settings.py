from pathlib import Path

# Путь к папке с файлами (можно заменить на абсолютный путь при необходимости)
STORAGE_PATH = Path(__file__).parent / "../data"

# Формат даты для колонки «Дата операции»: ДД.ММ.ГГГГ ЧЧ:ММ:СС
DATETIME_FORMAT_DMY_HMS = "%d.%m.%Y %H:%M:%S"
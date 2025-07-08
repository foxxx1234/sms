# FreeSMS/i18n.py

import os
import sys
import json

# 1) Путь к папке этого файла (FreeSMS/)
MODULE_PATH = os.path.abspath(os.path.dirname(__file__))
# 2) Путь к корню проекта — одна папка выше (где лежит runserver.py, translations.json, config.json)
PROJECT_ROOT = os.path.abspath(os.path.join(MODULE_PATH, os.pardir))

def _find_file(fname: str) -> str:
    """
    Ищет fname сначала в MODULE_PATH, затем в PROJECT_ROOT.
    Возвращает полный путь, если найден, иначе пустую строку.
    """
    for base in (MODULE_PATH, PROJECT_ROOT):
        candidate = os.path.join(base, fname)
        if os.path.isfile(candidate):
            return candidate
    return ""

# Составляем пути
TRANSLATIONS_PATH = _find_file("translations.json")
CONFIG_PATH       = _find_file("config.json")

# Загружаем переводы один раз
try:
    if not TRANSLATIONS_PATH:
        raise FileNotFoundError(f"translations.json not found in {MODULE_PATH} or {PROJECT_ROOT}")
    with open(TRANSLATIONS_PATH, encoding="utf-8") as f:
        TRANSLATIONS = json.load(f)
except Exception as e:
    print(f"Warning: не удалось загрузить translations.json: {e}")
    TRANSLATIONS = {}

# Кэш текущего языка
_current_lang = None

def get_language() -> str:
    """
    Читает язык из config.json (ключ "language") или возвращает "en".
    Один раз сохраняет результат в _current_lang.
    """
    global _current_lang
    if _current_lang:
        return _current_lang

    if not CONFIG_PATH:
        _current_lang = "en"
        return _current_lang

    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        _current_lang = cfg.get("language", "en")
    except Exception:
        _current_lang = "en"
    return _current_lang

def set_language(lang: str) -> None:
    """
    Записывает выбранный язык в config.json (ключ "language").
    """
    global _current_lang
    _current_lang = lang

    if not PROJECT_ROOT:
        return

    cfg = {}
    # Пробуем загрузить существующую конфигурацию
    cfg_path = os.path.join(PROJECT_ROOT, "config.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    cfg["language"] = lang
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing config.json: {e}")

def t(key: str, lang: str = None) -> str:
    """
    Переводит по ключу "section.sub.key". Если lang не передан — берётся из get_language().
    Если перевод не найден — возвращает сам ключ.
    """
    if lang is None:
        lang = get_language()

    node = TRANSLATIONS
    for part in key.split("."):
        if not isinstance(node, dict):
            break
        node = node.get(part, {})

    # Если node — dict, значит не нашли конкретную строку, но можем выдать node[lang]
    if isinstance(node, dict):
        return node.get(lang, node.get("en", key))
    # Иначе node — строка, либо пустое значение
    return str(node or key)

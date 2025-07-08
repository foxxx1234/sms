# FreeSMS/modem_utils.py

import os
import json
import re
import time

import serial
import serial.tools.list_ports
import pycountry

from .i18n import t, get_language

# Путь к файлу operators.json (лежит в корне проекта)
BASE = os.path.dirname(__file__)
OPS_PATH = os.path.abspath(os.path.join(BASE, "..", "operators.json"))

# Загружаем список операторов: MCC+MNC → "ccc-operator"
try:
    with open(OPS_PATH, encoding="utf-8") as f:
        _ops_list = json.load(f)
except FileNotFoundError:
    _ops_list = []

# Собираем маппинг "MCCMNC" → "ccc-operator"
OPS_MAP = {}
for entry in _ops_list:
    mcc = entry.get("mcc", "")
    mnc = entry.get("mnc", "")
    country_code = entry.get("country", "").lower()   # ожидаем трибуквенный код страны
    operator_code = entry.get("operator", "").lower()
    if mcc and mnc and country_code and operator_code:
        OPS_MAP[mcc + mnc] = f"{country_code}-{operator_code}"


def list_modem_ports():
    """
    Возвращает список доступных COM-портов для модемов.
    """
    return [p.device for p in serial.tools.list_ports.comports()]


def send_at_command(port, command, timeout=1.0):
    """
    Отправляет AT-команду на модем и возвращает ответ.
    """
    try:
        with serial.Serial(port, 115200, timeout=timeout) as modem:
            modem.write((command + "\r").encode("utf-8", errors="ignore"))
            time.sleep(0.2)
            return modem.read_all().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def parse_signal(response, lang):
    """
    Разбирает ответ '+CSQ: <rssi>,<ber>' и возвращает 'rssi (quality)',
    где quality берётся из переводов signal.none/bad/medium/good.
    """
    m = re.search(r"\+CSQ: (\d+),", response)
    if not m:
        return t("signal.error", lang)
    rssi = int(m.group(1))
    if rssi == 99:
        key = "signal.none"
    elif rssi <= 9:
        key = "signal.bad"
    elif rssi <= 14:
        key = "signal.medium"
    else:
        key = "signal.good"
    quality = t(key, lang)
    return f"{rssi} ({quality})"


def get_country_from_imsi(imsi):
    """
    Определяет трёхбуквенный ISO-код страны по MCC из IMSI.
    """
    if len(imsi) < 3 or not imsi[:3].isdigit():
        return ""
    mcc = imsi[:3]
    country = pycountry.countries.get(numeric=mcc)
    if country:
        return country.alpha_3.lower()
    return ""


def get_operator_from_imsi(imsi):
    """
    Определяет код оператора вида 'ccc-operator' по первым 5 цифрам IMSI.
    """
    if len(imsi) >= 5 and imsi[:5].isdigit():
        return OPS_MAP.get(imsi[:5], "unknown")
    return "unknown"


def get_modem_info(port, lang=None):
    """
    Собирает информацию по модему на указанном порту.
    Принимает:
      - port (строка)
      - lang (код языка, например 'ru', 'en', 'zh') — опционально.
    Возвращает dict с полями:
      port, model, vendor, imsi, operator, sim_country,
      network, signal, status, sms, voice, imei, iccid, cpin, ussd
    """
    if lang is None:
        lang = get_language()

    info = {"port": port}

    # Проверка связи
    at_ok = send_at_command(port, "AT")
    # Статус OK мы оставляем в английском (и не переводим),
    # а отсутствие ответа локализуем
    info["status"] = "OK" if "OK" in at_ok else t("status.no_response", lang)

    # Основные данные
    info["model"] = send_at_command(port, "AT+CGMM").strip() or "—"
    info["vendor"] = send_at_command(port, "AT+CGMI").strip() or "—"

    # IMSI → оператор и страна SIM
    imsi = send_at_command(port, "AT+CIMI").strip()
    info["imsi"] = imsi or "—"
    info["operator"] = get_operator_from_imsi(imsi) or "—"
    info["sim_country"] = get_country_from_imsi(imsi) or "—"

    # Статус регистрации в сети
    reg = send_at_command(port, "AT+CREG?") or ""
    # строка Connected/Disconnected лучше локализовать на уровне шаблона
    info["network"] = "Connected" if "+CREG: 0,1" in reg or "+CREG: 0,5" in reg else "Disconnected"

    # Качество сигнала
    csq = send_at_command(port, "AT+CSQ") or ""
    info["signal"] = parse_signal(csq, lang)

    # Дополнительные данные
    info["imei"] = send_at_command(port, "AT+CGSN").strip() or "—"
    info["iccid"] = send_at_command(port, "AT+CCID").strip() or "—"
    cpin = send_at_command(port, "AT+CPIN?").strip()
    info["cpin"] = cpin.replace("CPIN:", "").strip() if cpin else "—"

    # Заглушки для SMS/Voice/USSD (реализуем позже)
    info["sms"] = 0
    info["voice"] = 0
    info["ussd"] = ""

    return info

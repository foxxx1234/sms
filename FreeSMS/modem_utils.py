# FreeSMS/modem_utils.py

import os
import json
import re
import time
import glob

import serial
import serial.tools.list_ports
import pycountry

from .i18n import t, get_language

# Путь к файлу operators.json (лежит в корне проекта)
BASE = os.path.dirname(__file__)
OPS_PATH = os.path.abspath(os.path.join(BASE, "..", "operators.json"))

# Загружаем список операторов: MCC+MNC → "ccc-operator" и MCC → страна
try:
    with open(OPS_PATH, encoding="utf-8") as f:
        _ops_list = json.load(f)
except FileNotFoundError:
    _ops_list = []

# Собираем маппинги
OPS_MAP = {}
COUNTRY_MAP = {}
for entry in _ops_list:
    mcc = str(entry.get("mcc", ""))
    mnc = str(entry.get("mnc", ""))
    country_code = entry.get("country", "").lower()  # ожидаем трибуквенный код страны
    operator_code = entry.get("operator", "").lower()
    if mcc and mnc and country_code and operator_code:
        OPS_MAP[mcc + mnc] = f"{country_code}-{operator_code}"
        COUNTRY_MAP.setdefault(mcc, country_code)


def list_modem_ports():
    """Возвращает список доступных COM-портов для модемов."""
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if ports:
        return ports

    # Fallback scanning for environments where pyserial returns nothing
    extra = []
    if os.name == "nt":
        # Windows: probe common COM range
        for i in range(1, 257):
            extra.append(f"COM{i}")
    else:
        # POSIX systems: typical modem device patterns
        patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/cu.*", "/dev/tty.*"]
        for pat in patterns:
            extra.extend(glob.glob(pat))
    return extra


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


def extract_data(response: str) -> str:
    """Возвращает только полезные данные из ответа модема."""
    if not response:
        return ""
    text = response.strip()
    text = re.sub(r'^AT[^\n]*\n', '', text, flags=re.IGNORECASE)
    text = text.replace('\r', '').replace('\n', ' ').strip()
    if text.upper().endswith('OK'):
        text = text[:-2].strip()
    m = re.search(r'\+[^:]+:\s*"?([^" ]+)"?', text)
    if m:
        return m.group(1).strip()
    if text.startswith('+'):
        text = text[1:].strip()
    return text


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
    if mcc in COUNTRY_MAP:
        return COUNTRY_MAP[mcc]
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


def get_country_from_iccid(iccid: str) -> str:
    """Возвращает трёхбуквенный ISO-код страны по MCC из ICCID."""
    digits = re.sub(r"\D", "", iccid)
    if not digits.startswith("89") or len(digits) < 5:
        return ""
    mcc = digits[2:5]
    if mcc in COUNTRY_MAP:
        return COUNTRY_MAP[mcc]
    country = pycountry.countries.get(numeric=mcc)
    if country:
        return country.alpha_3.lower()
    return ""


def get_operator_from_iccid(iccid: str) -> str:
    """Возвращает код оператора вида 'ccc-operator' по ICCID."""
    digits = re.sub(r"\D", "", iccid)
    if not digits.startswith("89") or len(digits) < 7:
        return "unknown"
    mcc = digits[2:5]
    # Сначала пробуем MNC из трёх цифр
    if len(digits) >= 8:
        mnc = digits[5:8]
        code = OPS_MAP.get(mcc + mnc)
        if code:
            return code
    # Затем пробуем двухзначный MNC
    mnc = digits[5:7]
    return OPS_MAP.get(mcc + mnc, "unknown")


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
    # Статус модема
    info["status"] = t("status.ok", lang) if "OK" in at_ok else t("status.no_response", lang)

    # Основные данные
    info["model"] = extract_data(send_at_command(port, "AT+CGMM")) or "—"
    info["vendor"] = extract_data(send_at_command(port, "AT+CGMI")) or "—"

    # IMSI → оператор и страна SIM
    imsi = extract_data(send_at_command(port, "AT+CIMI"))
    info["imsi"] = imsi or "—"
    operator = get_operator_from_imsi(imsi)
    sim_country = get_country_from_imsi(imsi)

    iccid = extract_data(send_at_command(port, "AT+CCID"))
    info["iccid"] = iccid or "—"
    if operator == "unknown" and iccid:
        operator = get_operator_from_iccid(iccid)
    if not sim_country and iccid:
        sim_country = get_country_from_iccid(iccid)

    info["operator"] = operator or "—"
    info["sim_country"] = sim_country or "—"

    # Статус регистрации в сети
    reg = send_at_command(port, "AT+CREG?") or ""
    # Локализованный статус регистрации в сети
    if "+CREG: 0,1" in reg or "+CREG: 0,5" in reg:
        info["network"] = t("network_state.connected", lang)
    else:
        info["network"] = t("network_state.disconnected", lang)

    # Качество сигнала
    csq = send_at_command(port, "AT+CSQ") or ""
    info["signal"] = parse_signal(csq, lang)

    # Дополнительные данные
    info["imei"] = extract_data(send_at_command(port, "AT+CGSN")) or "—"
    cpin = extract_data(send_at_command(port, "AT+CPIN?"))
    info["cpin"] = cpin or "—"

    # Номер телефона SIM-карты
    phone_resp = send_at_command(port, "AT+CNUM").strip()
    m = re.search(r'"([+\\d]+)"', phone_resp)
    info["phone"] = m.group(1) if m else "—"

    # Заглушки для SMS/Voice/USSD (реализуем позже)
    info["sms"] = 0
    info["voice"] = 0
    info["ussd"] = ""

    return info


# FreeSMS/modem_utils.py

import os
import json
import re
import glob

import pycountry
import asyncio
import gammu

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
    try:
        devices = gammu.GetConfig(0)
        ports = [devices.get("Device")] if devices else []
        if ports and ports[0]:
            return ports
    except Exception:
        ports = []

    # Fallback scanning when Gammu detection fails
    if os.name == "nt":
        ports.extend([f"COM{i}" for i in range(1, 257)])
    else:
        patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/cu.*", "/dev/tty.*"]
        for pat in patterns:
            ports.extend(glob.glob(pat))
    return ports


def send_at_command(port, command, timeout=1.0):
    """Отправляет AT-команду через библиотеку Gammu и возвращает ответ."""
    try:
        sm = gammu.StateMachine()
        sm.ReadConfig()
        sm.SetConfig(0, {"Device": port, "Connection": "at"})
        sm.Init()
        return sm.SendATCommand(command)
    except Exception:
        return ""


async def send_at_command_async(port, command, timeout=1.0):
    """Асинхронная отправка AT-команды через Gammu."""
    return await asyncio.to_thread(send_at_command, port, command, timeout)


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

    sm = gammu.StateMachine()
    sm.ReadConfig()
    sm.SetConfig(0, {"Device": port, "Connection": "at"})

    try:
        sm.Init()
        info["status"] = t("status.ok", lang)
    except Exception:
        info["status"] = t("status.no_response", lang)
        return info

    try:
        info["model"] = sm.GetModel().get("Model", "—")
    except Exception:
        info["model"] = "—"

    try:
        info["vendor"] = sm.GetManufacturer().get("Manufacturer", "—")
    except Exception:
        info["vendor"] = "—"

    try:
        imsi = sm.GetSIMIMSI()
        info["imsi"] = imsi
    except Exception:
        imsi = ""
        info["imsi"] = "—"
    operator = get_operator_from_imsi(imsi)
    sim_country = get_country_from_imsi(imsi)

    try:
        iccid = sm.GetICC()
        info["iccid"] = iccid
    except Exception:
        iccid = ""
        info["iccid"] = "—"

    if operator == "unknown" and iccid:
        operator = get_operator_from_iccid(iccid)
    if not sim_country and iccid:
        sim_country = get_country_from_iccid(iccid)

    info["operator"] = operator or "—"
    info["sim_country"] = sim_country or "—"

    try:
        net = sm.GetNetworkInfo()
        if net:
            info["network"] = t("network_state.connected", lang)
        else:
            info["network"] = t("network_state.disconnected", lang)
    except Exception:
        info["network"] = t("network_state.disconnected", lang)

    try:
        sig = sm.GetSignalQuality()
        rssi = sig.get("SignalStrength", 99)
        csq_resp = f"+CSQ: {rssi},0"
        info["signal"] = parse_signal(csq_resp, lang)
    except Exception:
        info["signal"] = t("signal.error", lang)

    try:
        info["imei"] = sm.GetIMEI()
    except Exception:
        info["imei"] = "—"

    try:
        info["cpin"] = sm.GetSecurityStatus()
    except Exception:
        info["cpin"] = "—"

    try:
        nums = sm.GetOwnNumbers()
        if nums:
            info["phone"] = nums[0].get("Number", "—")
        else:
            info["phone"] = "—"
    except Exception:
        info["phone"] = "—"

    info["sms"] = 0
    info["voice"] = 0
    info["ussd"] = ""

    return info


async def get_modem_info_async(port, lang=None, timeout=1.0):
    """Асинхронное получение информации о модеме через Gammu."""
    return await asyncio.to_thread(get_modem_info, port, lang)


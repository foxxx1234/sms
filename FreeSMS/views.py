# FreeSMS/views.py

import json
from flask import (
    render_template, request, jsonify, make_response, current_app
)
from . import app
from .modem_utils import list_modem_ports, get_modem_info
from .i18n import t, get_language, set_language

# Заглушки для правил и USSD-конфига
RULES = []
USSD_CONFIG = {}

# ---------- Основная страница ----------
@app.route("/", methods=["GET"])
def index():
    # язык из cookie или из config.json
    lang = request.cookies.get("lang", get_language())
    set_language(lang)

    # сканируем все порты
    ports = list_modem_ports()

    # Заголовки таблицы: все переводы и текущий язык отдельно
    translations = current_app.config["TRANSLATIONS"]["table_headers"]
    hdr_keys = list(translations.keys())
    labels_all = {k: translations[k] for k in hdr_keys}
    labels_cur = {k: t(f"table_headers.{k}", lang) for k in hdr_keys}

    # кнопки и вкладки из конфигурации
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]

    return render_template(
        "index.html",
        ports=ports,
        labels=labels_cur,
        labels_all=labels_all,
        hdr_keys=hdr_keys,
        buttons=buttons,
        tabs=tabs,
        lang=lang,
        t=t
    )

# ---------- Страницы телефонов, сообщений, правил и т.д. ----------
@app.route("/phones", methods=["GET"])
def phones():
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]
    return render_template(
        "phones.html",
        buttons=buttons,
        tabs=tabs,
        labels_all=current_app.config["TRANSLATIONS"]["table_headers"],
        lang=lang,
        t=t
    )

@app.route("/received", methods=["GET"])
def received():
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]
    return render_template(
        "received.html",
        buttons=buttons,
        tabs=tabs,
        labels_all=current_app.config["TRANSLATIONS"]["table_headers"],
        lang=lang,
        t=t
    )

@app.route("/sent", methods=["GET"])
def sent():
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]
    return render_template(
        "sent.html",
        buttons=buttons,
        tabs=tabs,
        labels_all=current_app.config["TRANSLATIONS"]["table_headers"],
        lang=lang,
        t=t
    )

@app.route("/rules", methods=["GET"])
def rules():
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]
    return render_template(
        "rules.html",
        rules_list=RULES,
        buttons=buttons,
        tabs=tabs,
        labels_all=current_app.config["TRANSLATIONS"]["table_headers"],
        lang=lang,
        t=t
    )

@app.route("/no_rules", methods=["GET"])
def no_rules():
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]
    return render_template(
        "no_rules.html",
        buttons=buttons,
        tabs=tabs,
        labels_all=current_app.config["TRANSLATIONS"]["table_headers"],
        lang=lang,
        t=t
    )

@app.route("/forward", methods=["GET"])
def forward():
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]
    return render_template(
        "forward.html",
        buttons=buttons,
        tabs=tabs,
        labels_all=current_app.config["TRANSLATIONS"]["table_headers"],
        lang=lang,
        t=t
    )

@app.route("/settings", methods=["GET"])
def settings():
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    buttons = current_app.config["TRANSLATIONS"]["buttons"]
    tabs    = current_app.config["TRANSLATIONS"]["tabs"]
    return render_template(
        "settings.html",
        buttons=buttons,
        tabs=tabs,
        labels_all=current_app.config["TRANSLATIONS"]["table_headers"],
        lang=lang,
        t=t
    )

# ---------- Смена языка ----------
@app.route("/set_language", methods=["POST"])
def set_lang():
    data = request.get_json(force=True) or {}
    lang = data.get("lang")
    if lang:
        set_language(lang)
        resp = make_response(jsonify(success=True))
        resp.set_cookie("lang", lang, max_age=30*24*3600)
        return resp
    return jsonify(success=False), 400

# ---------- API по ТЗ ----------
@app.route("/api/scan_ports", methods=["GET"])
def api_scan_ports():
    return jsonify(ports=list_modem_ports())

@app.route("/api/modem_info", methods=["POST"])
def api_modem_info():
    data = request.get_json(force=True) or {}
    port = data.get("port")
    if not port:
        return jsonify(error="no port"), 400
    info = get_modem_info(port, get_language())
    return jsonify(info)

@app.route("/api/connect", methods=["POST"])
def api_connect():
    data = request.get_json(force=True) or {}
    sel = data.get("ports") or list_modem_ports()
    results = {}
    lang = request.cookies.get("lang", get_language())
    for p in sel:
        try:
            results[p] = get_modem_info(p, lang)
        except Exception as e:
            results[p] = {"error": str(e)}
    return jsonify(success=True, ports=sel, results=results)

@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    data = request.get_json(force=True) or {}
    sel = data.get("ports") or list_modem_ports()
    return jsonify(success=True, ports=sel)

@app.route("/api/port_find", methods=["POST"])
def api_port_find():
    return jsonify(success=True)

@app.route("/api/port_sort", methods=["POST"])
def api_port_sort():
    return jsonify(success=True)

@app.route("/api/ussd", methods=["POST"])
def api_ussd():
    return jsonify(success=True)

@app.route("/api/sms_records", methods=["GET"])
def api_sms_records():
    return jsonify(records=[])

@app.route("/api/sms_content", methods=["GET"])
def api_sms_content():
    return jsonify(content={})

@app.route("/api/send_sms", methods=["POST"])
def api_send_sms():
    return jsonify(success=True)

@app.route("/api/sms_status", methods=["GET"])
def api_sms_status():
    return jsonify(status="sent")

@app.route("/api/dial_number", methods=["POST"])
def api_dial_number():
    return jsonify(success=True)

@app.route("/api/dial_port", methods=["POST"])
def api_dial_port():
    return jsonify(success=True)

@app.route("/api/ussd_number", methods=["POST"])
def api_ussd_number():
    return jsonify(success=True)

@app.route("/api/ussd_port", methods=["POST"])
def api_ussd_port():
    return jsonify(success=True)

@app.route("/api/at_number", methods=["POST"])
def api_at_number():
    return jsonify(success=True)

@app.route("/api/at_port", methods=["POST"])
def api_at_port():
    return jsonify(success=True)

@app.route("/api/set_port_number", methods=["POST"])
def api_set_port_number():
    return jsonify(success=True)

@app.route("/api/reboot_port", methods=["POST"])
def api_reboot_port():
    return jsonify(success=True)

@app.route("/api/activate_sim_pool_number", methods=["POST"])
def api_activate_sim_pool_number():
    return jsonify(success=True)

@app.route("/api/activate_sim_pool_port", methods=["POST"])
def api_activate_sim_pool_port():
    return jsonify(success=True)

@app.route("/api/next_sim_pool_all", methods=["POST"])
def api_next_sim_pool_all():
    return jsonify(success=True)

@app.route("/api/next_sim_pool_port", methods=["POST"])
def api_next_sim_pool_port():
    return jsonify(success=True)

@app.route("/api/set_port_state", methods=["POST"])
def api_set_port_state():
    return jsonify(success=True)

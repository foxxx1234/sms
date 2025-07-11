# FreeSMS/views.py

import json
import time
import os
import concurrent.futures
import asyncio
from flask import (
    render_template, request, jsonify, make_response, current_app
)
from deepdiff import DeepDiff
from . import app
from . import event_logger
from .modem_utils import (
    list_modem_ports,
    get_modem_info,
    get_modem_info_async,
)
from .i18n import t, get_language, set_language

# Maximum number of worker threads for concurrent modem operations
MAX_WORKERS = 10


def render_page(template: str, **context):
    """Render template with common translation context."""
    lang = request.cookies.get("lang", get_language())
    set_language(lang)
    base_ctx = {
        "buttons": current_app.config["TRANSLATIONS"]["buttons"],
        "tabs": current_app.config["TRANSLATIONS"]["tabs"],
        "labels_all": current_app.config["TRANSLATIONS"]["table_headers"],
        "logs": current_app.config["TRANSLATIONS"].get("log_messages", {}),
        "lang": lang,
        "t": t,
    }
    base_ctx.update(context)
    return render_template(template, **base_ctx)

# Заглушки для правил и USSD-конфига
RULES = []
USSD_CONFIG = {}

# ---------- Основная страница ----------
@app.route("/", methods=["GET"])
def index():
    """Display the modem overview page."""
    lang = request.cookies.get("lang", get_language())
    set_language(lang)

    ports = list_modem_ports()
    translations = current_app.config["TRANSLATIONS"]["table_headers"]
    hdr_keys = list(translations.keys())
    labels_all = {k: translations[k] for k in hdr_keys}
    labels_cur = {k: t(f"table_headers.{k}", lang) for k in hdr_keys}

    return render_page(
        "index.html",
        ports=ports,
        labels=labels_cur,
        labels_all=labels_all,
        hdr_keys=hdr_keys,
    )

# ---------- Страницы телефонов, сообщений, правил и т.д. ----------
@app.route("/phones", methods=["GET"])
def phones():
    """Show saved phone book entries."""
    return render_page("phones.html")

@app.route("/received", methods=["GET"])
def received():
    """Display received SMS messages."""
    return render_page("received.html")

@app.route("/sent", methods=["GET"])
def sent():
    """Show sent SMS messages."""
    return render_page("sent.html")

@app.route("/rules", methods=["GET"])
def rules():
    """Display rules configuration."""
    return render_page("rules.html", rules_list=RULES)

@app.route("/no_rules", methods=["GET"])
def no_rules():
    """Fallback page when no rules are defined."""
    return render_page("no_rules.html")

@app.route("/forward", methods=["GET"])
def forward():
    """Display SIM forwarding configuration."""
    return render_page("forward.html")

@app.route("/settings", methods=["GET"])
def settings():
    """Application settings page."""
    return render_page("settings.html")

# ---------- Смена языка ----------
@app.route("/set_language", methods=["POST"])
def set_lang():
    """Persist selected language in the config and cookie."""
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

@app.route("/api/connect", methods=["GET", "POST"])
def api_connect():
    """Connect to selected ports and return modem info.

    Accepts JSON ``{"ports": [..]}`` and returns modem info either as a
    traditional aggregated JSON object or streams per-port results when the
    client requests ``text/event-stream``.

    POST  - returns a single JSON object for all ports (legacy behaviour)
    GET   - streams JSON objects per port via Server-Sent Events
    """

    if request.method == "GET":
        # EventStream mode: ?ports=COM1&ports=COM2 or comma separated
        ports = request.args.getlist("ports")
        if not ports:
            ports_arg = request.args.get("ports", "")
            if ports_arg:
                ports = [p.strip() for p in ports_arg.split(",") if p.strip()]
        if not ports:
            ports = list_modem_ports()

        lang = request.cookies.get("lang", get_language())

        def generate():
            try:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(ports), MAX_WORKERS)
                ) as executor:
                    future_map = {
                        executor.submit(get_modem_info, p, lang): p for p in ports
                    }
                    for future in concurrent.futures.as_completed(future_map):
                        p = future_map[future]
                        try:
                            info = future.result()
                        except Exception as e:
                            info = {"port": p, "status": str(e)}
                        if "port" not in info:
                            info["port"] = p
                        event_logger.log_event("port_connected", port=p)
                        yield f"data: {json.dumps(info)}\n\n"
            except GeneratorExit:
                return
            except Exception as e:
                event_logger.log_event("sse_error", details=str(e))
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return current_app.response_class(generate(), mimetype="text/event-stream")

    # POST behaviour - return aggregated JSON for all ports
    data = request.get_json(force=True) or {}
    ports = data.get("ports") or list_modem_ports()
    lang = request.cookies.get("lang", get_language())

    # Check if the client expects streaming responses
    if request.headers.get("Accept") == "text/event-stream":
        def generate():
            try:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(ports), MAX_WORKERS)
                ) as executor:
                    future_map = {
                        executor.submit(get_modem_info, p, lang): p for p in ports
                    }
                    for future in concurrent.futures.as_completed(future_map):
                        p = future_map[future]
                        try:
                            info = future.result()
                        except Exception as e:
                            info = {"port": p, "status": str(e)}
                        if "port" not in info:
                            info["port"] = p
                        event_logger.log_event("port_connected", port=p)
                        yield f"data: {json.dumps(info)}\n\n"
            except GeneratorExit:
                return
            except Exception as e:
                event_logger.log_event("sse_error", details=str(e))
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return current_app.response_class(generate(), mimetype="text/event-stream")

    # Legacy behaviour – aggregate results in a single JSON
    results = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(len(ports), MAX_WORKERS)
    ) as executor:
        future_map = {
            executor.submit(get_modem_info, p, lang): p for p in ports
        }
        for future in concurrent.futures.as_completed(future_map):
            p = future_map[future]
            try:
                results[p] = future.result()
            except Exception as e:
                results[p] = {"error": str(e)}
            event_logger.log_event("port_connected", port=p)

    return jsonify(success=True, ports=ports, results=results)

@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    data = request.get_json(force=True) or {}
    sel = data.get("ports") or list_modem_ports()
    for p in sel:
        event_logger.log_event("port_disconnected", port=p)
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
    data = request.get_json(force=True) or {}
    port = data.get("port")
    phone = data.get("phone")
    text = data.get("text", "")
    event_logger.log_event("sms_outgoing", port=port, phone=phone, details=text)
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

@app.route("/api/log", methods=["POST"])
def api_log():
    data = request.get_json(force=True) or {}
    msg = data.get("message")
    port = data.get("port")
    if not msg:
        return jsonify(success=False, error="no message"), 400
    try:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        fname = f"{port}.log" if port else "app.log"
        path = os.path.join(log_dir, fname)
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        event_logger.log_event("log", port=port, details=msg)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

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


@app.route("/api/monitor", methods=["GET"])
def api_monitor():
    """Stream modem state changes via Server-Sent Events."""
    requested_ports = request.args.getlist("ports")
    lang = request.cookies.get("lang", get_language())

    def generate():
        prev_by_port = {}
        prev_by_sim = {}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while True:
                current_ports = requested_ports or list_modem_ports()
                tasks = [get_modem_info_async(p, lang) for p in current_ports]
                results = loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )
                new_by_port = {}
                new_by_sim = {}
                for p, res in zip(current_ports, results):
                    if isinstance(res, Exception):
                        event_logger.log_event(
                            "monitor_error", port=p, details=str(res)
                        )
                        info = prev_by_port.get(p)
                        if info:
                            new_by_port[p] = info
                            iccid_saved = info.get("iccid")
                            if iccid_saved:
                                new_by_sim[iccid_saved] = info
                        continue
                    info = res
                    port = info.get("port")
                    iccid = info.get("iccid")
                    if not iccid or iccid == "\u2014":
                        iccid = None
                    imsi = info.get("imsi")
                    if not iccid and imsi and imsi != "\u2014":
                        iccid = imsi

                    old_info_sim = prev_by_sim.get(iccid) if iccid else None
                    old_info_port = prev_by_port.get(port)
                    old_info = old_info_sim if old_info_sim is not None else old_info_port
                    dd = DeepDiff(old_info or {}, info, ignore_order=True).to_dict()
                    diff = {}
                    for path, change in dd.get("values_changed", {}).items():
                        key = path.strip("root[").strip("]'").split("['")[-1]
                        if key != "port":
                            diff[key] = change.get("new_value")
                    for path in dd.get("dictionary_item_added", []):
                        key = path.strip("root[").strip("]'").split("['")[-1]
                        if key != "port":
                            diff[key] = info.get(key)
                    for path in dd.get("dictionary_item_removed", []):
                        key = path.strip("root[").strip("]'").split("['")[-1]
                        if key != "port":
                            diff[key] = None

                    old_port = old_info.get("port") if old_info else None
                    if iccid and old_port and old_port != port:
                        diff["moved_from"] = old_port

                    if diff:
                        diff["port"] = port
                        yield f"data: {json.dumps(diff)}\n\n"
                    new_by_port[port] = info
                    if iccid:
                        new_by_sim[iccid] = info

                removed_ports = set(prev_by_port) - set(new_by_port)
                for rp in removed_ports:
                    yield f"data: {json.dumps({'port': rp, 'removed': True})}\n\n"
                removed_sims = set(prev_by_sim) - set(new_by_sim)
                for sim in removed_sims:
                    rp = prev_by_sim[sim].get("port")
                    if rp and rp not in removed_ports:
                        yield f"data: {json.dumps({'port': rp, 'removed': True})}\n\n"

                prev_by_port = new_by_port
                prev_by_sim = new_by_sim
                time.sleep(1.0)
        except GeneratorExit:
            return
        except Exception as e:
            event_logger.log_event("monitor_stream_error", details=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            loop.close()

    return current_app.response_class(generate(), mimetype="text/event-stream")

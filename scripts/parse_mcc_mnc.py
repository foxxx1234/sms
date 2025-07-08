import json
import re
import requests
import pycountry

URL = "https://cdn.jsdelivr.net/npm/mccmnc.json@1.2.0/+esm"


def fetch_data():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    text = resp.text.strip()
    if text.startswith("export default"):
        text = text[len("export default"):].strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    return json.loads(text)


def generate_ops(data):
    result = []
    entries = data.values() if isinstance(data, dict) else data
    for entry in entries:
        mcc = entry.get("mcc")
        mnc = entry.get("mnc")
        alpha2 = (
            entry.get("iso")
            or entry.get("countryCode")
            or entry.get("country_code")
        )
        name = (
            entry.get("network")
            or entry.get("brand")
            or entry.get("operator")
            or entry.get("name")
        )
        if not (mcc and mnc and alpha2 and name):
            continue
        country = pycountry.countries.get(alpha_2=alpha2.upper())
        if not country:
            continue
        result.append({
            "mcc": str(mcc),
            "mnc": str(mnc),
            "country": country.alpha_3.lower(),
            "operator": re.sub(r"\s+", "-", name.strip().lower()),
        })
    return result


def main():
    data = fetch_data()
    ops = generate_ops(data)
    with open("operators.json", "w", encoding="utf-8") as f:
        json.dump(ops, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

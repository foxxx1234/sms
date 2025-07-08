import json
import requests
import pycountry

URL = "https://raw.githubusercontent.com/nyaruka/carriers/master/carriers/fixtures/mccmnc.json"


def fetch_operator_data():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def generate_ops_list(data):
    result = []
    for entry in data:
        mcc = entry.get("mcc")
        mnc = entry.get("mnc")
        country_alpha2 = entry.get("iso")
        operator_name = entry.get("name")
        if not (mcc and mnc and country_alpha2 and operator_name):
            continue
        country = pycountry.countries.get(alpha_2=country_alpha2.upper())
        if not country:
            continue
        country_code = country.alpha_3.lower()
        operator_code = operator_name.lower().replace(" ", "-")
        result.append({
            "mcc": mcc,
            "mnc": mnc,
            "country": country_code,
            "operator": operator_code
        })
    return result


def main():
    data = fetch_operator_data()
    ops_list = generate_ops_list(data)
    with open("operators.json", "w", encoding="utf-8") as f:
        json.dump(ops_list, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

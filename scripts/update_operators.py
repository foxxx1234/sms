import json
import requests
import pycountry

# Source with up-to-date MCC/MNC information
# This dataset contains three-letter country codes
URL = "https://raw.githubusercontent.com/atis--/mccmnc.json/master/mccmnc.json"


def fetch_operator_data():
    """Download raw MCC/MNC data from the remote table."""
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _extract_entries(data):
    """Return a list of operator entries regardless of wrapping structure."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("records", "data", "mccmnc", "operators"):
            entries = data.get(key)
            if isinstance(entries, list):
                return entries
        if len(data) == 1 and isinstance(next(iter(data.values())), list):
            return next(iter(data.values()))
    return []


def _normalize_entry(entry):
    mcc = entry.get("mcc") or entry.get("MCC")
    mnc = entry.get("mnc") or entry.get("MNC")
    operator_name = (
        entry.get("brand")
        or entry.get("operator")
        or entry.get("network")
        or entry.get("name")
    )

    country_alpha3 = (
        entry.get("countryCode")
        or entry.get("country_code")
        or entry.get("alpha3")
        or entry.get("alpha_3")
    )
    country_alpha2 = (
        entry.get("iso")
        or entry.get("iso2")
        or entry.get("alpha2")
        or entry.get("alpha_2")
    )

    if not country_alpha3 and country_alpha2:
        country = pycountry.countries.get(alpha_2=country_alpha2.upper())
        if country:
            country_alpha3 = country.alpha_3

    if not (mcc and mnc and operator_name and country_alpha3):
        return None

    return {
        "mcc": str(mcc),
        "mnc": str(mnc),
        "country": country_alpha3.lower(),
        "operator": operator_name.lower().replace(" ", "-"),
    }


def generate_ops_list(data):
    result = []
    for entry in _extract_entries(data):
        normalized = _normalize_entry(entry)
        if normalized:
            result.append(normalized)
    return result


def main():
    data = fetch_operator_data()
    ops_list = generate_ops_list(data)
    with open("operators.json", "w", encoding="utf-8") as f:
        json.dump(ops_list, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

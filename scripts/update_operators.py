import json
import requests
import pycountry

# Source with up‑to‑date MCC/MNC information.  The atis-- dataset provides MCC
# and MNC codes along with two-letter country codes.  We convert those to
# three-letter ISO codes.
URL = "https://raw.githubusercontent.com/atis--/mccmnc.json/master/mccmnc.json"


def fetch_operator_data():
    """Download raw MCC/MNC data from the remote table."""
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def generate_ops_list(data):
    """Convert raw JSON from the atis-- table to operators.json format."""
    result = []
    # The atis-- dataset may be either a list or a mapping keyed by MCC/MNC.
    entries = data.values() if isinstance(data, dict) else data

    for entry in entries:
        mcc = entry.get("mcc")
        mnc = entry.get("mnc")
        # Some variants use "iso" or "countryCode" for the 2-letter country code
        country_alpha2 = (
            entry.get("iso")
            or entry.get("countryCode")
            or entry.get("country_code")
        )

        # Operator name can be under different keys
        operator_name = (
            entry.get("network")
            or entry.get("brand")
            or entry.get("operator")
            or entry.get("name")
        )

        # If mcc/mnc are missing but the key is of the form "mccmnc"
        if (not mcc or not mnc) and isinstance(entry, dict):
            key = entry.get("mccmnc")
            if not key and isinstance(data, dict):
                # Attempt to derive from dictionary key when possible
                for k, v in data.items():
                    if v is entry:
                        key = k
                        break
            if key and key.isdigit() and len(key) >= 5:
                mcc = mcc or key[:3]
                mnc = mnc or key[3:]

        if not (mcc and mnc and country_alpha2 and operator_name):
            continue

        country = pycountry.countries.get(alpha_2=country_alpha2.upper())
        if not country:
            continue

        country_code = country.alpha_3.lower()
        operator_code = operator_name.lower().replace(" ", "-")
        result.append({
            "mcc": str(mcc),
            "mnc": str(mnc),
            "country": country_code,
            "operator": operator_code,
        })

    return result


def main():
    data = fetch_operator_data()
    ops_list = generate_ops_list(data)
    with open("operators.json", "w", encoding="utf-8") as f:
        json.dump(ops_list, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

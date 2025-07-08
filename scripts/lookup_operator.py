import sys
from FreeSMS.modem_utils import (
    get_operator_from_imsi,
    get_operator_from_iccid,
    get_country_from_imsi,
    get_country_from_iccid,
)


def main():
    if len(sys.argv) != 2:
        print("Usage: lookup_operator.py <IMSI|ICCID>")
        return 1
    code = sys.argv[1].strip()
    if code.isdigit() and len(code) >= 5:
        operator = get_operator_from_imsi(code)
        country = get_country_from_imsi(code)
    else:
        operator = get_operator_from_iccid(code)
        country = get_country_from_iccid(code)
    print(f"operator: {operator}\ncountry: {country}")


if __name__ == "__main__":
    raise SystemExit(main())

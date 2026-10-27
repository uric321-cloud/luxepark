#!/usr/bin/env python3
"""
Refresh pricing and availability in assets/data.js from the property's RentCafe feed.

Sources (first one that applies wins):
  1. --json FILE      a saved RentCafe "apartmentavailability" API response
  2. --csv FILE       a simple sheet the office can keep: unit,plan,rent,available,unitId
  3. RENTCAFE_TOKEN + RENTCAFE_PROPERTY_ID in the environment  → fetched live

RentCafe Marketing API (ask Yardi / RentCafe support for the token, it is per property):
  https://api.rentcafe.com/rentcafeapi.aspx?requestType=apartmentavailability&apiToken=TOKEN&propertyId=ID

Usage:
  python3 tools/update_pricing.py --json export.json
  python3 tools/update_pricing.py --csv units.csv
  RENTCAFE_TOKEN=... RENTCAFE_PROPERTY_ID=... python3 tools/update_pricing.py
  add --dry-run to print the result without writing.
"""
import argparse, csv, datetime as dt, json, os, re, sys, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "assets", "data.js")

PLAN_BY_NAME = {"shortleaf": "shortleaf", "longleaf": "longleaf", "slash": "slash", "loblolly": "loblolly"}
PLAN_BY_FPID = {"4624296": "shortleaf", "4624310": "longleaf", "4624311": "slash", "4624312": "loblolly"}

def plan_slug(name="", fpid=""):
    if str(fpid) in PLAN_BY_FPID: return PLAN_BY_FPID[str(fpid)]
    key = re.sub(r"[^a-z]", "", (name or "").lower())
    for k, v in PLAN_BY_NAME.items():
        if k in key: return v
    raise SystemExit(f"Unknown floor plan: name={name!r} id={fpid!r}")

def norm_date(v):
    """'Available' / '' / 'Now' -> None, otherwise ISO date. Dates on or before today also mean now."""
    if v is None: return None
    s = str(v).strip()
    if not s or s.lower() in ("available", "now", "available now", "immediate"): return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            d = dt.datetime.strptime(s[:19] if "T" in s else s, fmt).date()
            return None if d <= dt.date.today() else d.isoformat()
        except ValueError: pass
    raise SystemExit(f"Unrecognised date: {s!r}")

def norm_rent(v):
    s = re.sub(r"[^\d.]", "", str(v)); return int(round(float(s))) if s else 0

def from_rentcafe(payload):
    """Map a RentCafe apartmentavailability response (list of dicts) to our unit shape."""
    rows = payload if isinstance(payload, list) else payload.get("units") or payload.get("Units") or payload.get("data") or []
    out = []
    for r in rows:
        g = lambda *keys: next((r[k] for k in keys if k in r and r[k] not in (None, "")), "")
        num = re.sub(r"\D", "", str(g("ApartmentName", "UnitName", "unit", "Unit")))
        if len(num) != 4: continue
        rent = norm_rent(g("MinimumRent", "Rent", "rent", "MarketRent"))
        if not rent: continue
        out.append(dict(num=num, plan=plan_slug(g("FloorplanName", "Floorplan", "plan"), g("FloorplanId", "FloorPlanID", "floorplanId")),
                        rent=rent, avail=norm_date(g("AvailableDate", "AvailabilityDate", "available", "DateAvailable")),
                        unitId=str(g("ApartmentId", "UnitID", "UnitId", "unitId"))))
    return out

def from_csv(path):
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            num = re.sub(r"\D", "", r["unit"]); out.append(dict(num=num, plan=plan_slug(r.get("plan", "")), rent=norm_rent(r["rent"]), avail=norm_date(r.get("available")), unitId=str(r.get("unitId", "")).strip()))
    return out

def fetch_live():
    token, pid = os.environ.get("RENTCAFE_TOKEN"), os.environ.get("RENTCAFE_PROPERTY_ID")
    if not (token and pid): return None
    q = urllib.parse.urlencode({"requestType": "apartmentavailability", "apiToken": token, "propertyId": pid})
    with urllib.request.urlopen(f"https://api.rentcafe.com/rentcafeapi.aspx?{q}", timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def render_units(units):
    units = sorted(units, key=lambda u: (["shortleaf", "longleaf", "slash", "loblolly"].index(u["plan"]), u["rent"], u["num"]))
    lines = [f'    U({u["num"]}, "{u["plan"]}", {u["rent"]}, {json.dumps(u["avail"])}, {u["unitId"] or "null"}),' for u in units]
    return "  const UNITS = [\n" + "\n".join(lines) + "\n  ];"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json"); ap.add_argument("--csv"); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    if a.json: units = from_rentcafe(json.load(open(a.json)))
    elif a.csv: units = from_csv(a.csv)
    else:
        payload = fetch_live()
        if payload is None: sys.exit("No source. Pass --json or --csv, or set RENTCAFE_TOKEN and RENTCAFE_PROPERTY_ID.")
        units = from_rentcafe(payload)
    if not units: sys.exit("No units parsed; refusing to write an empty list.")
    src = open(DATA, encoding="utf-8").read()
    new = re.sub(r"  const UNITS = \[\n.*?\n  \];", lambda m: render_units(units), src, count=1, flags=re.S)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    new = re.sub(r'const UPDATED = "[^"]*";', f'const UPDATED = "{stamp}";', new)
    if a.dry_run: print(render_units(units)); print("UPDATED", stamp); return
    open(DATA, "w", encoding="utf-8").write(new)
    print(f"Wrote {len(units)} units to assets/data.js (updated {stamp}).")

if __name__ == "__main__": main()

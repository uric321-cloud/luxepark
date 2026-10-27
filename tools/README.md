# Keeping prices live

`assets/data.js` is the only place pricing and availability live. Run the updater and every page
(home finder, layouts, property map, list, drawer, specials estimate) picks the change up.

```bash
# from a RentCafe API export
python3 tools/update_pricing.py --json export.json
# from a sheet the office keeps (see units.example.csv)
python3 tools/update_pricing.py --csv units.csv
# fully automatic (daily GitHub Action in .github/workflows/refresh-pricing.yml)
RENTCAFE_TOKEN=... RENTCAFE_PROPERTY_ID=... python3 tools/update_pricing.py
```

Getting the token: the RentCafe "Marketing API" key is issued per property by Yardi / RentCafe
support (ask your RentCafe account rep for the apartmentavailability API token and the property id).
The luxeparkga.com pages themselves sit behind bot protection, so the API is the supported route.

# Tour bookings and contact messages

Both forms POST JSON to the URL in the `data-endpoint` attribute (`[data-booking]` modal and the
contact form). Any form backend works: Formspree, Basin, a Zapier catch hook, or a tiny serverless
function that emails the office and drops the lead into RentCafe CRM. Until an endpoint is set,
guided bookings hand the chosen slot to the RentCafe scheduler page and self-guided bookings go to Tour24.

# 3D walkthroughs

Set `matterport: "MODELID"` on a plan in `assets/data.js` (from a Matterport share link) and the
3D tour tab, plus every apartment drawer for that plan, switch from "coming soon" to the live model.

import zipfile, shapefile, json, shutil, os

TIGER_ZIP = r"c:\Users\mrnai\Downloads\Dove House\data_by_criteria\data_by_criteria\06_rural_urban_service_gaps\tiger_boundaries\cb_2022_us_county_500k.zip"
OUT_FILE  = r"c:\Users\mrnai\Downloads\Dove House\data_by_criteria\powerbi_ready\indiana_counties.json"
TMP_DIR   = "_tiger_tmp_indiana"

with zipfile.ZipFile(TIGER_ZIP) as z:
    z.extractall(TMP_DIR)

shp_file = next(f for f in os.listdir(TMP_DIR) if f.endswith(".shp"))
sf = shapefile.Reader(os.path.join(TMP_DIR, shp_file))
fields = [f[0] for f in sf.fields[1:]]

features = []
for sr in sf.shapeRecords():
    rec = dict(zip(fields, sr.record))
    if rec.get("STATEFP") == "18":
        fips = rec["STATEFP"] + rec["COUNTYFP"]
        features.append({
            "type": "Feature",
            "id": fips,
            "properties": {"GEOID": fips, "NAME": rec["NAME"]},
            "geometry": sr.shape.__geo_interface__
        })

geojson = {"type": "FeatureCollection", "features": features}

with open(OUT_FILE, "w") as f:
    json.dump(geojson, f)

shutil.rmtree(TMP_DIR, ignore_errors=True)
print(f"Written {len(features)} Indiana counties to {OUT_FILE}")

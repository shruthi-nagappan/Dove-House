import json
import topojson as tp

INPUT  = r"c:\Users\mrnai\Downloads\Dove House\data_by_criteria\powerbi_ready\indiana_counties.json"
OUTPUT = r"c:\Users\mrnai\Downloads\Dove House\data_by_criteria\powerbi_ready\indiana_counties.topojson"

with open(INPUT) as f:
    geojson = json.load(f)

# Build id->name lookup from geojson before conversion
id_map = {ft["id"]: ft["properties"]["NAME"] for ft in geojson["features"]}

topo = tp.Topology(geojson, prequantize=True, topology=True)
result = json.loads(topo.to_json())

# Power BI Shape Map matches Location field against geometry "id" values.
# Ensure each geometry carries the FIPS id from the original feature.
obj_key = list(result["objects"].keys())[0]
geoms = result["objects"][obj_key]["geometries"]

for geom in geoms:
    props = geom.get("properties") or {}
    # topojson lib preserves original properties; GEOID holds the FIPS string
    fips = props.get("GEOID") or props.get("id")
    if fips:
        geom["id"] = fips

with open(OUTPUT, "w") as f:
    json.dump(result, f)

print(f"Saved TopoJSON with {len(geoms)} counties → {OUTPUT}")

# Verify a sample id
sample = geoms[0]
print("Sample geometry id:", sample.get("id"), "| properties:", sample.get("properties"))

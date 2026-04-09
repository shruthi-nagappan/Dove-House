"""
Populate RDF Graph with Indiana Hospital Discharge Data
Loads CSV data and creates RDF instances in the ontology
"""

import pandas as pd
from pathlib import Path
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS

DOVE_HOME = Path(__file__).resolve().parents[2]
ONTO_DIR = DOVE_HOME / "IndianaHospitalDischarges/ontology"
IDOH_DATA = DOVE_HOME / "data_by_criteria/02_access_health_social_services/indiana_hospital_discharge"
DATASET_DIR = IDOH_DATA / "Dataset"

# Load ontology
g = Graph()
g.parse(ONTO_DIR / "IndianaHospital_Ontology.ttl", format="turtle")

EX = Namespace("http://example.org/hospital/")
g.bind("ex", EX)

# Load CSV files
print("Loading CSV files...")
aprdrg_df = pd.read_csv(DATASET_DIR / "APRDRG_IN2024_updated.csv")
msdrg_df = pd.read_csv(DATASET_DIR / "MSDRG_IN2024_updated.csv")
diag_df = pd.read_csv(DATASET_DIR / "DIAG_IN2024_updated.csv")
proc_df = pd.read_csv(DATASET_DIR / "PROC_IN2024_updated.csv")

print(f"✓ APRDRG: {len(aprdrg_df):,} rows")
print(f"✓ MS-DRG: {len(msdrg_df):,} rows")
print(f"✓ Diagnosis: {len(diag_df):,} rows")
print(f"✓ Procedure: {len(proc_df):,} rows")

# Create unique entities
print("\nCreating entities...")

hospitals = set(aprdrg_df['HOSPITAL_ID'].unique())
payers = {1: "Medicare", 2: "Medicaid", 3: "Commercial", 4: "Self-Pay"}
aprdrgs = set(aprdrg_df['APRDRG'].unique())
msdrgs = set(msdrg_df['MSDRG'].unique())
diagnoses = set(diag_df['DIAGNOSIS_1'].unique())
procedures = set(proc_df['PROCEDURE_1'].unique())

# Add Hospital instances
for hospital_id in hospitals:
    hosp_uri = EX[f"Hospital_{hospital_id}"]
    g.add((hosp_uri, RDF.type, EX.Hospital))
    g.add((hosp_uri, EX.hospitalID, Literal(int(hospital_id))))
    g.add((hosp_uri, RDFS.label, Literal(f"Hospital {hospital_id}")))

print(f"  ✓ {len(hospitals)} hospitals")

# Add Payer instances
for payer_code, payer_name in payers.items():
    payer_uri = EX[f"Payer_{payer_code}"]
    g.add((payer_uri, RDF.type, EX.Payer))
    g.add((payer_uri, EX.payerCode, Literal(payer_code)))
    g.add((payer_uri, EX.payerName, Literal(payer_name)))
    g.add((payer_uri, RDFS.label, Literal(payer_name)))

print(f"  ✓ {len(payers)} payers")

# Add APR-DRG instances
for aprdrg in aprdrgs:
    aprdrg_uri = EX[f"APRDRG_{aprdrg}"]
    g.add((aprdrg_uri, RDF.type, EX.APRDRG))
    g.add((aprdrg_uri, EX.aprdrg, Literal(int(aprdrg))))
    g.add((aprdrg_uri, RDFS.label, Literal(f"APR-DRG {aprdrg}")))

print(f"  ✓ {len(aprdrgs)} APR-DRGs")

# Add MS-DRG instances
for msdrg in msdrgs:
    msdrg_uri = EX[f"MSDRG_{msdrg}"]
    g.add((msdrg_uri, RDF.type, EX.MSDRG))
    g.add((msdrg_uri, EX.msdrgCode, Literal(int(msdrg))))
    g.add((msdrg_uri, RDFS.label, Literal(f"MS-DRG {msdrg}")))

print(f"  ✓ {len(msdrgs)} MS-DRGs")

# Add Diagnosis instances
for diag in diagnoses:
    diag_uri = EX[f"Diagnosis_{diag}"]
    g.add((diag_uri, RDF.type, EX.Diagnosis))
    g.add((diag_uri, EX.diagnosisCode, Literal(str(diag))))
    g.add((diag_uri, RDFS.label, Literal(str(diag))))

print(f"  ✓ {len(diagnoses)} diagnoses")

# Add Procedure instances
for proc in procedures:
    proc_uri = EX[f"Procedure_{proc}"]
    g.add((proc_uri, RDF.type, EX.Procedure))
    g.add((proc_uri, EX.procedureCode, Literal(str(proc))))
    g.add((proc_uri, RDFS.label, Literal(str(proc))))

print(f"  ✓ {len(procedures)} procedures")

# Add Discharge Record instances (aggregated by hospital, payer, and APR-DRG)
print("\nCreating discharge records...")
discharge_count = 0

# Aggregate by hospital, payer, and APR-DRG
discharge_data = aprdrg_df.groupby(['HOSPITAL_ID', 'PAYOR1', 'APRDRG']).agg({
    'PATS': 'sum',
    'TC': 'sum',
    'TD': 'sum'
}).reset_index()

for idx, row in discharge_data.iterrows():
    discharge_uri = EX[f"DischargeRecord_{idx}"]
    g.add((discharge_uri, RDF.type, EX.DischargeRecord))
    g.add((discharge_uri, EX.fromHospital, EX[f"Hospital_{int(row['HOSPITAL_ID'])}"]))
    g.add((discharge_uri, EX.hasPayer, EX[f"Payer_{int(row['PAYOR1'])}"]))
    g.add((discharge_uri, EX.hasAPRDRG, EX[f"APRDRG_{int(row['APRDRG'])}"]))
    g.add((discharge_uri, EX.patientCount, Literal(int(row['PATS']))))
    g.add((discharge_uri, EX.totalCharge, Literal(float(row['TC']))))
    g.add((discharge_uri, EX.totalDays, Literal(int(row['TD']))))
    
    if row['PATS'] > 0:
        avg_charge = row['TC'] / row['PATS']
        avg_los = row['TD'] / row['PATS']
        g.add((discharge_uri, EX.averageCharge, Literal(float(avg_charge))))
        g.add((discharge_uri, EX.averageLOS, Literal(float(avg_los))))
    
    discharge_count += 1

print(f"  ✓ {discharge_count:,} discharge records")

# Serialize to Turtle
print("\nSerializing to Turtle...")
g.serialize(destination=str(ONTO_DIR / "IndianaHospital_Instances.ttl"), format="turtle")

print(f"✓ RDF instances created: {ONTO_DIR / 'IndianaHospital_Instances.ttl'}")
print(f"  Total triples: {len(g):,}")
print(f"\nOntology: IndianaHospital_Ontology.ttl")
print(f"Instances: IndianaHospital_Instances.ttl")

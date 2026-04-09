"""
Create OWL Ontology for Indiana Hospital Discharge Data
Generates semantic ontology schema for hospital discharge domain
"""

from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD
from datetime import datetime

# Create graph
g = Graph()

# Define namespaces
EX = Namespace("http://example.org/hospital/")
VAEM = Namespace("http://www.linkedmodel.org/schema/vaem#")

g.bind("ex", EX)
g.bind("vaem", VAEM)
g.bind("owl", OWL)
g.bind("rdfs", RDFS)
g.bind("rdf", RDF)

# Ontology metadata
ontology_uri = EX.IndianaHospitalDischargeOntology
g.add((ontology_uri, RDF.type, OWL.Ontology))
g.add((ontology_uri, RDFS.label, Literal("Indiana Hospital Discharge Ontology")))
g.add((ontology_uri, RDFS.comment, Literal("Semantic ontology for Indiana hospital discharge data 2024")))
g.add((ontology_uri, OWL.versionInfo, Literal("1.0")))
g.add((ontology_uri, VAEM.createdDate, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

# Define Classes
classes = {
    "DischargeRecord": "Hospital discharge record with patient metrics",
    "Hospital": "Healthcare facility",
    "City": "Geographic city",
    "Payer": "Healthcare payment source",
    "GovernmentPayer": "Government-funded healthcare payer",
    "CommercialPayer": "Private commercial healthcare payer",
    "SelfPayer": "Self-pay patient",
    "MSDRG": "Medicare Severity Diagnosis Related Group classification",
    "APRDRG": "All Patient Refined Diagnosis Related Group classification",
    "SeverityLevel": "Patient severity classification",
    "Minor": "Minor severity level",
    "Moderate": "Moderate severity level",
    "Major": "Major severity level",
    "Extreme": "Extreme severity level",
    "Diagnosis": "Medical diagnosis code",
    "Procedure": "Medical procedure code"
}

for class_name, description in classes.items():
    class_uri = EX[class_name]
    g.add((class_uri, RDF.type, OWL.Class))
    g.add((class_uri, RDFS.label, Literal(class_name)))
    g.add((class_uri, RDFS.comment, Literal(description)))

# Add subclass relationships
subclass_map = {
    "GovernmentPayer": "Payer",
    "CommercialPayer": "Payer",
    "SelfPayer": "Payer",
    "Minor": "SeverityLevel",
    "Moderate": "SeverityLevel",
    "Major": "SeverityLevel",
    "Extreme": "SeverityLevel"
}

for subclass, superclass in subclass_map.items():
    g.add((EX[subclass], RDFS.subClassOf, EX[superclass]))

# Define Object Properties
object_properties = {
    "fromHospital": ("DischargeRecord", "Hospital", "Discharge is from hospital"),
    "hasPayer": ("DischargeRecord", "Payer", "Discharge has payer"),
    "hasAPRDRG": ("DischargeRecord", "APRDRG", "Discharge classified with APR-DRG"),
    "hasMSDRG": ("DischargeRecord", "MSDRG", "Discharge classified with MS-DRG"),
    "hasSeverity": ("DischargeRecord", "SeverityLevel", "Discharge has severity level"),
    "hasDiagnosis": ("DischargeRecord", "Diagnosis", "Discharge includes diagnosis"),
    "hasProcedure": ("DischargeRecord", "Procedure", "Discharge includes procedure"),
    "locatedIn": ("Hospital", "City", "Hospital is located in city")
}

for prop_name, (domain, range_class, description) in object_properties.items():
    prop_uri = EX[prop_name]
    g.add((prop_uri, RDF.type, OWL.ObjectProperty))
    g.add((prop_uri, RDFS.label, Literal(prop_name)))
    g.add((prop_uri, RDFS.comment, Literal(description)))
    g.add((prop_uri, RDFS.domain, EX[domain]))
    g.add((prop_uri, RDFS.range, EX[range_class]))

# Define Datatype Properties
datatype_properties = {
    "hospitalID": (EX.Hospital, XSD.integer, "Hospital identifier"),
    "facilityName": (EX.Hospital, XSD.string, "Hospital facility name"),
    "cityName": (EX.City, XSD.string, "City name"),
    "msdrgCode": (EX.MSDRG, XSD.integer, "MS-DRG code"),
    "msdrgDescription": (EX.MSDRG, XSD.string, "MS-DRG description"),
    "aprdrg": (EX.APRDRG, XSD.integer, "APR-DRG code"),
    "aprdrg_description": (EX.APRDRG, XSD.string, "APR-DRG description"),
    "diagnosisCode": (EX.Diagnosis, XSD.string, "ICD-10 diagnosis code"),
    "diagnosisDescription": (EX.Diagnosis, XSD.string, "Diagnosis description"),
    "procedureCode": (EX.Procedure, XSD.string, "CPT procedure code"),
    "procedureDescription": (EX.Procedure, XSD.string, "Procedure description"),
    "patientCount": (EX.DischargeRecord, XSD.integer, "Number of patients"),
    "totalCharge": (EX.DischargeRecord, XSD.decimal, "Total charges in USD"),
    "totalDays": (EX.DischargeRecord, XSD.integer, "Total days of care"),
    "averageCharge": (EX.DischargeRecord, XSD.decimal, "Average charge per patient"),
    "averageLOS": (EX.DischargeRecord, XSD.decimal, "Average length of stay in days"),
    "payerCode": (EX.Payer, XSD.integer, "Payer identifier code"),
    "payerName": (EX.Payer, XSD.string, "Payer organization name"),
    "severityScore": (EX.SeverityLevel, XSD.integer, "Severity score (1-4)")
}

for prop_name, (domain, datatype, description) in datatype_properties.items():
    prop_uri = EX[prop_name]
    g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
    g.add((prop_uri, RDFS.label, Literal(prop_name)))
    g.add((prop_uri, RDFS.comment, Literal(description)))
    g.add((prop_uri, RDFS.domain, domain))
    g.add((prop_uri, RDFS.range, datatype))

# Serialize to Turtle format
g.serialize(destination='../ontology/IndianaHospital_Ontology.ttl', format='turtle')
print(f"✓ Ontology created: ontology/IndianaHospital_Ontology.ttl")
print(f"  Triples: {len(g)}")
print(f"  Classes: {len(classes)}")
print(f"  Object Properties: {len(object_properties)}")
print(f"  Datatype Properties: {len(datatype_properties)}")

# Indiana Hospital Discharge Data — OWL Ontology

## Overview

This repository contains a comprehensive OWL ontology for 2024 Indiana hospital discharge data, structured in the style of the NIDA Drug Dictionary Ontology.

## Files

### Primary Files

- **`create_ontology.py`** - Main Python script to generate the ontology
- **`IndianaHospital_Ontology.ttl`** - Generated OWL ontology in Turtle format (234 triples, 16 classes, 31 properties)

### Source Data

- **`Dataset/`** - Four CSV files with 2024 Indiana discharge metrics:
  - `APRDRG_IN2024_updated.csv` - All Patient Refined DRG classifications
  - `DIAG_IN2024_updated.csv` - ICD-10 diagnosis codes
  - `MSDRG_IN2024_updated.csv` - Medicare Severity DRG classifications
  - `PROC_IN2024_updated.csv` - ICD-10-PCS procedure codes

- **`requirements.txt`** - Python dependencies

### Documentation

- **`IndianaHospital_OntologySchema.ipynb`** - Jupyter notebook with ontology design
- **`IndianaHospital_PopulateInstances.ipynb`** - Notebook for populating instances from CSV data

## Ontology Structure

The ontology defines:

### Core Classes
- `DischargeRecord` - Central entity representing hospital discharge records with associated metrics
- `Hospital` - Healthcare facility
- `City` - Geographic location in Indiana
- `Payer` (with subtypes: GovernmentPayer, CommercialPayer, SelfPayer)
- `MSDRG` - Medicare Severity Diagnosis Related Group
- `APRDRG` - All Patient Refined Diagnosis Related Group
- `SeverityLevel` (with subtypes: Minor, Moderate, Major, Extreme)
- `Diagnosis` - ICD-10-CM diagnosis code
- `Procedure` - ICD-10-PCS procedure code

### Properties (Object & Datatype)

**Object Properties:**
- `fromHospital`, `hasPayer`, `hasMSDRG`, `hasAPRDRG`, `hasSeverity`, `hasDiagnosis`, `hasProcedure`, `locatedIn`

**Datatype Properties:**
- Hospital: `hospitalID`, `facilityName`
- Clinical: `msdrgCode`, `msdrgDescription`, `aprdrgCode`, `aprdrgDescription`, `diagnosisCode`, `diagnosisDescription`, `procedureCode`, `procedureDescription`
- Metrics: `totalPatientDischarges`, `dischargesWithCharges`, `totalCharges`, `totalDays`, `averageChargePerDischarge`, `averageLengthOfStay`
- Metadata: `datasetSource`, `reportingYear`

## Generating the Ontology

```bash
python create_ontology.py
```

This will create/update `IndianaHospital_Ontology.ttl` with 234 RDF triples.

## Dependencies

- Python 3.7+
- `rdflib` - For RDF/Turtle serialization

Install with:
```bash
pip install rdflib
```

## Data Source

2024 Indiana Hospital Discharge Data Files
https://www.in.gov/health/oda/hospital-discharge-data/2024-indiana-hospital-discharge-data-files/

## Ontology Design Principles

The ontology follows the NIDA Drug Dictionary Ontology pattern:

1. **Rich Metadata** - Each concept includes labels (English, German), comments, and SKOS annotations
2. **Semantic Hierarchy** - Clear subclass relationships (e.g., PayerTypes, SeverityLevels)
3. **Comprehensive Properties** - Both object properties (relationships) and datatype properties (attributes)
4. **Clinical Accuracy** - Proper representation of healthcare classification systems
5. **Extensibility** - Easy to add new classes, properties, or instances

## Authors

Indiana University NLP-Lab

## License

[Specify your license here]

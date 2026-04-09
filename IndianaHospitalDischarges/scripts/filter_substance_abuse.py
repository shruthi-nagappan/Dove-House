"""
Filter & Extract Substance Abuse Data
Extracts substance abuse and overdose admissions from raw hospital discharge data
Generates intermediate CSV files for visualization and analysis
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

DOVE_HOME = Path(__file__).resolve().parents[2]
IDOH_DATA = DOVE_HOME / "data_by_criteria/02_access_health_social_services/indiana_hospital_discharge"
DATASET_DIR = IDOH_DATA / "Dataset"
OUTPUT_DIR = IDOH_DATA / "outputs/data_exports"
LOCATION_DIR = IDOH_DATA / "outputs/location_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOCATION_DIR.mkdir(parents=True, exist_ok=True)

# MS-DRG codes related to substance abuse
SUBSTANCE_ABUSE_MSDRG = [876, 877, 878]

# PAYER MAPPING
PAYER_TYPE_MAP = {
    1: 'Government (Medicare)',
    2: 'Government (Medicaid)',
    3: 'Private (Commercial)',
    4: 'Self-Pay',
}

def load_data():
    """Load all data from CSV files."""
    print("\n" + "="*80)
    print("LOADING RAW DATA")
    print("="*80)
    
    aprdrg_df = pd.read_csv(DATASET_DIR / "APRDRG_IN2024_updated.csv")
    msdrg_df = pd.read_csv(DATASET_DIR / "MSDRG_IN2024_updated.csv")
    diag_df = pd.read_csv(DATASET_DIR / "DIAG_IN2024_updated.csv")
    
    print(f"✓ APRDRG: {len(aprdrg_df):,} rows")
    print(f"✓ MS-DRG: {len(msdrg_df):,} rows")
    print(f"✓ Diagnosis: {len(diag_df):,} rows")
    
    return aprdrg_df, msdrg_df, diag_df

def categorize_diagnosis(code):
    """Categorize ICD-10 code into substance abuse category."""
    code_prefix = code[:3] if len(code) >= 3 else code[:2]
    
    if code_prefix == 'F11': return 'Opioid Disorders'
    elif code_prefix == 'F12': return 'Cannabis Disorders'
    elif code_prefix == 'F13': return 'Sedative Disorders'
    elif code_prefix == 'F14': return 'Cocaine Disorders'
    elif code_prefix == 'F15': return 'Stimulant Disorders'
    elif code_prefix == 'F16': return 'Hallucinogen Disorders'
    elif code_prefix == 'F17': return 'Nicotine Dependence'
    elif code_prefix == 'F18': return 'Inhalant Disorders'
    elif code_prefix == 'F19': return 'Other Psychoactive Substances'
    elif code_prefix == 'F10': return 'Alcohol Disorders'
    elif code_prefix == 'T40': return 'Opioid Overdose'
    elif code_prefix == 'T41': return 'Other Drug Overdose'
    elif code_prefix == 'T42': return 'Drug Overdose'
    elif code_prefix == 'T43': return 'Drug Overdose'
    elif code_prefix == 'T44': return 'Drug Overdose'
    elif code_prefix == 'T45': return 'Drug Overdose'
    elif code_prefix == 'T46': return 'Drug Overdose'
    elif code_prefix == 'T47': return 'Drug Overdose'
    elif code_prefix == 'T48': return 'Drug Overdose'
    elif code_prefix == 'T49': return 'Drug Overdose'
    elif code_prefix == 'T50': return 'Drug Overdose'
    elif code == 'K292': return 'Alcohol Gastritis'
    elif code == 'E244': return 'Alcohol-Induced Hypoglycemia'
    else: return 'Other Substance Related'

def extract_substance_abuse_admissions(aprdrg_df, msdrg_df, diag_df):
    """Extract substance abuse and overdose related admissions."""
    print("\n" + "="*80)
    print("FILTERING SUBSTANCE ABUSE ADMISSIONS")
    print("="*80)
    
    # Filter diagnosis data for substance abuse codes
    prefixes = ('F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 
                'F10', 'T40', 'T41', 'T42', 'T43', 'T44', 'T45', 'T46', 'T47', 'T48', 
                'T49', 'T50', 'K29', 'E24')
    substance_diag = diag_df[diag_df['DIAGNOSIS_1'].str.startswith(prefixes)].copy()
    
    # Categorize each diagnosis
    substance_diag['SUBSTANCE_CATEGORY'] = substance_diag['DIAGNOSIS_1'].apply(
        lambda x: categorize_diagnosis(x)
    )
    
    # Add payer type
    substance_diag['PAYER_TYPE'] = substance_diag['PAYOR1'].map(PAYER_TYPE_MAP)
    
    # Calculate derived metrics
    substance_diag['AVG_CHARGE'] = substance_diag['TC'] / substance_diag['PATS']
    substance_diag['AVG_LOS'] = substance_diag['TD'] / substance_diag['PATS']
    
    # Filter MS-DRG for substance abuse codes
    substance_msdrg = msdrg_df[msdrg_df['MSDRG'].isin(SUBSTANCE_ABUSE_MSDRG)].copy()
    substance_msdrg['PAYER_TYPE'] = substance_msdrg['PAYOR1'].map(PAYER_TYPE_MAP)
    substance_msdrg['AVG_CHARGE'] = substance_msdrg['TC'] / substance_msdrg['PATS']
    substance_msdrg['AVG_LOS'] = substance_msdrg['TD'] / substance_msdrg['PATS']
    
    print(f"✓ Extracted {len(substance_diag):,} substance-abuse diagnosis records")
    print(f"✓ Extracted {len(substance_msdrg):,} substance-abuse MS-DRG records")
    
    return substance_diag, substance_msdrg

def analyze_and_aggregate(substance_diag, substance_msdrg, aprdrg_df):
    """Perform analysis and create aggregations."""
    print("\n" + "="*80)
    print("ANALYZING SUBSTANCE ABUSE DATA")
    print("="*80)
    
    # Overall statistics
    total_admissions = substance_diag['PATS'].sum()
    total_charges = substance_diag['TC'].sum()
    total_los = substance_diag['TD'].sum()
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"  Total Substance Abuse Admissions: {total_admissions:,}")
    print(f"  Total Charges: ${total_charges:,.0f}")
    print(f"  Avg Charge per Admission: ${total_charges / total_admissions:,.2f}")
    print(f"  Total Days of Care: {total_los:,}")
    print(f"  Avg Length of Stay: {total_los / total_admissions:.2f} days")
    
    # By category
    print(f"\n📋 ADMISSIONS BY SUBSTANCE CATEGORY:")
    category_stats = substance_diag.groupby('SUBSTANCE_CATEGORY').agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum'
    }).sort_values('PATS', ascending=False)
    
    for category, row in category_stats.iterrows():
        pct = (row['PATS'] / total_admissions) * 100
        avg_charge = row['TC'] / row['PATS']
        avg_los = row['TD'] / row['PATS']
        print(f"  {category:30s}: {int(row['PATS']):6,} ({pct:5.1f}%) | ${avg_charge:>10,.0f} | {avg_los:.2f} days")
    
    # Top 10 hospitals
    print(f"\n🏥 TOP 10 HOSPITALS BY SUBSTANCE ABUSE ADMISSIONS:")
    top_hospitals = substance_diag.groupby('HOSPITAL_ID').agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum'
    }).sort_values('PATS', ascending=False).head(10)
    
    for hospital_id, row in top_hospitals.iterrows():
        avg_charge = row['TC'] / row['PATS']
        avg_los = row['TD'] / row['PATS']
        print(f"  Hospital {hospital_id:3d}: {int(row['PATS']):6,} admissions | ${avg_charge:>10,.0f} avg | {avg_los:.2f} days")
    
    # Payer analysis
    print(f"\n💰 PAYER TYPE ANALYSIS:")
    payer_stats = substance_diag.groupby('PAYER_TYPE').agg({
        'PATS': 'sum',
        'TC': 'sum'
    }).sort_values('PATS', ascending=False)
    
    for payer, row in payer_stats.iterrows():
        if pd.notna(payer):
            pct = (row['PATS'] / total_admissions) * 100
            avg_charge = row['TC'] / row['PATS']
            print(f"  {payer:30s}: {int(row['PATS']):6,} ({pct:5.1f}%) | ${avg_charge:>10,.0f} avg")

def create_hospital_location_map(aprdrg_df):
    """Create a mapping of hospital IDs to locations."""
    print("\n" + "="*80)
    print("CREATING HOSPITAL LOCATION MAP")
    print("="*80)
    
    hospitals = aprdrg_df[['HOSPITAL_ID']].drop_duplicates().sort_values('HOSPITAL_ID')
    
    # Hospital names mapping
    hospital_names = {
        1: "Parkview Hospital, Ft. Wayne", 55: "Franciscan Health, Indianapolis",
        31: "IU Health Methodist, Indianapolis", 53: "Methodist Hospital, Indianapolis",
        62: "St. Vincent Hospital, Indianapolis", 63: "Wishard Memorial, Indianapolis",
        81: "Deaconess Hospital, Evansville", 82: "Ivy Tech, Evansville",
        103: "Terre Haute Regional", 109: "Bloomington Hospital",
        113: "Tipton Hospital", 125: "St. Vincent, Evansville",
        134: "Harrison Medical, Corydon", 138: "Clark Memorial, Jeffersonville",
        139: "Good Samaritan, Vincennes", 143: "Magnet Hospital", 
        477: "Hospital 477", 479: "Hospital 479", 756: "Hospital 756"
    }
    
    # Create location mapping
    hospital_locations = {}
    for hospital_id in hospitals['HOSPITAL_ID']:
        hospital_locations[hospital_id] = {
            'name': hospital_names.get(hospital_id, f'Hospital {hospital_id}'),
            'city': 'Indiana',
            'state': 'IN'
        }
    
    output_path = LOCATION_DIR / "hospital_locations.json"
    formatted_locations = {}
    for hospital_id, location in hospital_locations.items():
        formatted_locations[str(hospital_id)] = {
            'name': location['name'],
            'city': location['city'],
            'state': location['state'],
            'lat': None,
            'lon': None
        }
    
    with open(output_path, 'w') as f:
        json.dump(formatted_locations, f, indent=2)
    
    print(f"✓ Hospital location data saved to: hospital_locations.json")
    return hospital_locations

def export_data(substance_diag, substance_msdrg):
    """Export processed data to CSV files."""
    print("\n" + "="*80)
    print("EXPORTING DATA TO CSV")
    print("="*80)
    
    # Full diagnosis-level data
    substance_diag.to_csv(OUTPUT_DIR / 'substance_abuse_by_diagnosis.csv', index=False)
    print("✓ Exported: substance_abuse_by_diagnosis.csv")
    
    # Aggregated by hospital and category
    hospital_category = substance_diag.groupby(['HOSPITAL_ID', 'SUBSTANCE_CATEGORY']).agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum',
        'PAYOR1': 'first'
    }).reset_index()
    hospital_category['AVG_CHARGE'] = hospital_category['TC'] / hospital_category['PATS']
    hospital_category['AVG_LOS'] = hospital_category['TD'] / hospital_category['PATS']
    hospital_category.to_csv(OUTPUT_DIR / 'substance_abuse_by_hospital_category.csv', index=False)
    print("✓ Exported: substance_abuse_by_hospital_category.csv")
    
    # Aggregated by hospital and payer
    hospital_payer = substance_diag.groupby(['HOSPITAL_ID', 'PAYOR1']).agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum',
        'PAYER_TYPE': 'first',
        'SUBSTANCE_CATEGORY': lambda x: '; '.join(x.unique())
    }).reset_index()
    hospital_payer['AVG_CHARGE'] = hospital_payer['TC'] / hospital_payer['PATS']
    hospital_payer['AVG_LOS'] = hospital_payer['TD'] / hospital_payer['PATS']
    hospital_payer.to_csv(OUTPUT_DIR / 'substance_abuse_by_hospital_payer.csv', index=False)
    print("✓ Exported: substance_abuse_by_hospital_payer.csv")
    
    # Category summary
    category_summary = substance_diag.groupby('SUBSTANCE_CATEGORY').agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum'
    }).reset_index()
    category_summary['AVG_CHARGE'] = category_summary['TC'] / category_summary['PATS']
    category_summary['AVG_LOS'] = category_summary['TD'] / category_summary['PATS']
    category_summary = category_summary.sort_values('PATS', ascending=False)
    category_summary.to_csv(OUTPUT_DIR / 'substance_abuse_category_summary.csv', index=False)
    print("✓ Exported: substance_abuse_category_summary.csv")
    
    # Hospital summary
    hospital_summary = substance_diag.groupby('HOSPITAL_ID').agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum'
    }).reset_index()
    hospital_summary['AVG_CHARGE'] = hospital_summary['TC'] / hospital_summary['PATS']
    hospital_summary['AVG_LOS'] = hospital_summary['TD'] / hospital_summary['PATS']
    hospital_summary = hospital_summary.sort_values('PATS', ascending=False)
    hospital_summary.to_csv(OUTPUT_DIR / 'substance_abuse_hospital_summary.csv', index=False)
    print("✓ Exported: substance_abuse_hospital_summary.csv")
    
    # Payer summary
    payer_summary = substance_diag.groupby('PAYER_TYPE').agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum'
    }).reset_index()
    payer_summary['AVG_CHARGE'] = payer_summary['TC'] / payer_summary['PATS']
    payer_summary['AVG_LOS'] = payer_summary['TD'] / payer_summary['PATS']
    payer_summary = payer_summary.sort_values('PATS', ascending=False)
    payer_summary.to_csv(OUTPUT_DIR / 'substance_abuse_payer_summary.csv', index=False)
    print("✓ Exported: substance_abuse_payer_summary.csv")
    
    # MS-DRG summary
    msdrg_summary = substance_msdrg.groupby('MSDRG').agg({
        'PATS': 'sum',
        'TC': 'sum',
        'TD': 'sum'
    }).reset_index()
    msdrg_summary['AVG_CHARGE'] = msdrg_summary['TC'] / msdrg_summary['PATS']
    msdrg_summary['AVG_LOS'] = msdrg_summary['TD'] / msdrg_summary['PATS']
    msdrg_mapping = {876: "Alcohol/Drug Abuse - Left AMA", 
                     877: "Alcohol/Drug Abuse - With Therapy", 
                     878: "Alcohol/Drug Abuse - Without Therapy"}
    msdrg_summary['MSDRG_DESC'] = msdrg_summary['MSDRG'].map(msdrg_mapping)
    msdrg_summary.to_csv(OUTPUT_DIR / 'substance_abuse_msdrg_summary.csv', index=False)
    print("✓ Exported: substance_abuse_msdrg_summary.csv")

def main():
    print("\n" + "="*80)
    print("SUBSTANCE ABUSE DATA EXTRACTION & FILTERING")
    print("Indiana Hospital Discharge Data 2024")
    print("="*80)
    
    # Load raw data
    aprdrg_df, msdrg_df, diag_df = load_data()
    
    # Extract substance abuse admissions
    substance_diag, substance_msdrg = extract_substance_abuse_admissions(aprdrg_df, msdrg_df, diag_df)
    
    # Analyze data
    analyze_and_aggregate(substance_diag, substance_msdrg, aprdrg_df)
    
    # Create location mapping
    create_hospital_location_map(aprdrg_df)
    
    # Export processed data
    export_data(substance_diag, substance_msdrg)
    
    print("\n" + "="*80)
    print("✓ DATA EXTRACTION COMPLETE")
    print("="*80)
    print(f"\nAll intermediate CSV files saved to: {OUTPUT_DIR.absolute()}/")
    print("\nNext step: Run 'python visualize_substance_abuse.py' to generate visualizations")

if __name__ == '__main__':
    main()

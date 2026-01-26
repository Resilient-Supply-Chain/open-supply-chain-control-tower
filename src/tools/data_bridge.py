import csv
import json
import os
from datetime import datetime
from pathlib import Path

DEFAULT_CSV_SOURCE = "file_path/combined_risk_and_impact_predictions.csv"
DEFAULT_JSON_OUTPUT = "../oact/app/data/data_series.json"

# Full FIPS Mapping for California Counties (Name -> GeoID)
COUNTY_FIPS_MAP = {
    "Alameda": "06001", "Alpine": "06003", "Amador": "06005", "Butte": "06007",
    "Calaveras": "06009", "Colusa": "06011", "Contra Costa": "06013", "Del Norte": "06015",
    "El Dorado": "06017", "Fresno": "06019", "Glenn": "06021", "Humboldt": "06023",
    "Imperial": "06025", "Inyo": "06027", "Kern": "06029", "Kings": "06031",
    "Lake": "06033", "Lassen": "06035", "Los Angeles": "06037", "Madera": "06039",
    "Marin": "06041", "Mariposa": "06043", "Mendocino": "06045", "Merced": "06047",
    "Modoc": "06049", "Mono": "06051", "Monterey": "06053", "Napa": "06055",
    "Nevada": "06057", "Orange": "06059", "Placer": "06061", "Plumas": "06063",
    "Riverside": "06065", "Sacramento": "06067", "San Benito": "06069", "San Bernardino": "06071",
    "San Diego": "06073", "San Francisco": "06075", "San Joaquin": "06077", "San Luis Obispo": "06079",
    "San Mateo": "06081", "Santa Barbara": "06083", "Santa Clara": "06085", "Santa Cruz": "06087",
    "Shasta": "06089", "Sierra": "06091", "Siskiyou": "06093", "Solano": "06095",
    "Sonoma": "06097", "Stanislaus": "06099", "Sutter": "06101", "Tehama": "06103",
    "Trinity": "06105", "Tulare": "06107", "Tuolumne": "06109", "Ventura": "06111",
    "Yolo": "06113", "Yuba": "06115"
}

def get_risk_level(score: float) -> str:
    """Maps numerical score (0-1) to Frontend RiskLevel enum."""
    if score >= 0.7:
        return "high"
    elif score >= 0.3:
        return "moderate"
    else:
        return "low"

def get_risk_type(score: float, row_data: dict) -> str:
    """
    Determines the type of risk.
    Since the model predicts 'total_customers' (power), we default to Power Outage.
    """
    if score < 0.3:
        return "No Risk"
    
    # Example logic: checking if specific columns indicate other risks
    # For now, based on your CSV columns, 'Power Outage' is the primary implied risk
    return "Power Outage"

def run_conversion(*, source_file: Path, dest_file: Path) -> str:
    """Convert risk CSV into time-series JSON for UI consumption."""

    print(f"Reading from: {source_file}")

    if not source_file.exists():
        return f"Error: Source file not found at {source_file}"

    # Dictionary to store time series data
    # Key: Date String (YYYY-MM-DD), Value: List of County Objects
    time_series_data = {}

    with open(source_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            county_name = row.get("county_name", "").strip()
            date_str = row.get("date", "").strip() # Ensure no whitespace
            
            if not county_name or not date_str:
                continue

            # Get FIPS
            fips_id = COUNTY_FIPS_MAP.get(county_name)
            if not fips_id:
                # print(f"Warning: No FIPS for {county_name}")
                continue

            # Parse Score
            try:
                risk_score = float(row.get("predicted_risk_score", 0))
            except ValueError:
                risk_score = 0.0

            # Create County Object
            county_obj = {
                "id": fips_id,
                "name": county_name,
                "nameFull": f"{county_name} County",
                "state": "CA",
                "stateName": "California",
                "riskLevel": get_risk_level(risk_score),
                "riskType": get_risk_type(risk_score, row)
            }

            # Add to time series
            if date_str not in time_series_data:
                time_series_data[date_str] = []
            
            time_series_data[date_str].append(county_obj)

    # Write to JSON
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(time_series_data, f, indent=2)

    return (
        "Conversion Complete!\n"
        f"   Processed {len(time_series_data)} unique dates.\n"
        f"   Saved to: {dest_file}"
    )

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    source_file = (base_dir / DEFAULT_CSV_SOURCE).resolve()
    dest_file = (base_dir / DEFAULT_JSON_OUTPUT).resolve()
    result = run_conversion(source_file=source_file, dest_file=dest_file)
    print(result)

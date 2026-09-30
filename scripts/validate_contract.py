import pandas as pd

# ------------------------------------------------------------
# Load data (make sure these 2 files are in the SAME folder as this notebook)
# ------------------------------------------------------------
raw = pd.read_csv('incoming_visits_raw.csv', parse_dates=['visit_date','record_created_at'])
facilities = pd.read_csv('oyo_health_facilities.csv')

valid_facility_ids = set(facilities['facility_id'])
valid_visit_types = {'Outpatient','Inpatient','Emergency','Follow-up'}
SLO_HOURS = 24

# ------------------------------------------------------------
# Check every record against the 4 contract rules
# ------------------------------------------------------------
results = []
for _, row in raw.iterrows():
    reasons = []

    if pd.isna(row['patient_id']):
        reasons.append('missing_patient_id')

    if row['facility_id'] not in valid_facility_ids:
        reasons.append('invalid_facility_code')

    if row['visit_type'] not in valid_visit_types:
        reasons.append('invalid_visit_type')

    if pd.notna(row['visit_date']) and pd.notna(row['record_created_at']):
        gap_hours = (row['record_created_at'] - row['visit_date']).total_seconds() / 3600
        if gap_hours > SLO_HOURS:
            reasons.append('slo_breach')

    results.append({
        'visit_id': row['visit_id'],
        'valid': len(reasons) == 0,
        'violation_reasons': '; '.join(reasons)
    })

results_df = pd.DataFrame(results)
merged = raw.merge(results_df, on='visit_id')

# ------------------------------------------------------------
# Split into valid vs rejected - SAME columns in both, plus
# violation_reasons added only to the rejected file
# ------------------------------------------------------------
valid_visits = merged[merged['valid']].drop(columns=['valid', 'violation_reasons'])
rejected = merged[~merged['valid']].drop(columns=['valid'])

# Clean up integer columns so they don't get saved as decimals (e.g. 322.0)
int_cols = ['visit_id', 'patient_id', 'department_id', 'attending_staff_id', 'appointment_id']
for col in int_cols:
    valid_visits[col] = valid_visits[col].astype('Int64')
    rejected[col] = rejected[col].astype('Int64')

valid_visits.to_csv('visits_valid.csv', index=False)
rejected.to_csv('rejected_records_log.csv', index=False)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------
print(f"Total incoming records: {len(raw)}")
print(f"Accepted (valid):       {len(valid_visits)}")
print(f"Rejected (violations):  {len(rejected)}")
print(f"\nvalid_visits columns   ({len(valid_visits.columns)}): {list(valid_visits.columns)}")
print(f"rejected columns       ({len(rejected.columns)}): {list(rejected.columns)}")
print("\nViolation breakdown:")
print(rejected['violation_reasons'].str.split('; ').explode().value_counts())

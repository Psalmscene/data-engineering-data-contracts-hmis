import pandas as pd
import numpy as np
import random

random.seed(42)
np.random.seed(42)

# ------------------------------------------------------------
# Load everything needed
# ------------------------------------------------------------
raw = pd.read_csv('incoming_visits_raw.csv', parse_dates=['visit_date','record_created_at'])
valid_visits = pd.read_csv('visits_valid.csv')
rejected = pd.read_csv('rejected_records_log.csv')
patients = pd.read_csv('patients.csv', parse_dates=['date_of_birth'])
diagnoses = pd.read_csv('diagnoses.csv')   # already filtered to the 1,760 valid visits
treatments = pd.read_csv('treatments.csv') # already filtered to the 1,760 valid visits

# Real patient age lookup (as of 2026-01-01, matching generation logic)
patients['age'] = ((pd.Timestamp('2026-01-01') - patients['date_of_birth']).dt.days // 365)
age_lookup = dict(zip(patients['patient_id'], patients['age']))
GLOBAL_MEAN_AGE = int(patients['age'].mean())
print(f"Global mean age (used for imputation where patient link is broken): {GLOBAL_MEAN_AGE}")

# ------------------------------------------------------------
# Confirm the framing explicitly: incoming_visits_raw is exactly
# the union of visits_valid and rejected_records. This means the
# "Dirty" model built below is genuinely trained on the raw,
# as-arrived data (minus only the held-out test slice, removed
# purely for fair evaluation), not on an artificially combined
# dataset assembled after the fact.
# ------------------------------------------------------------
assert set(raw['visit_id']) == set(valid_visits['visit_id']) | set(rejected['visit_id']), \
    "raw should equal valid + rejected exactly"
print(f"Confirmed: incoming_visits_raw ({len(raw)}) = visits_valid ({len(valid_visits)}) + rejected_records ({len(rejected)})")

# ------------------------------------------------------------
# Same clinical realism rule used in generate_data.py, needed here
# to assign a diagnosis + TRUE outcome for the 60 missing-patient_id
# rows, which never got one during the original generation step
# (since that step skipped any row without a usable patient_id).
# ------------------------------------------------------------
diagnosis_options = [
    ('A09','Diarrhoea and gastroenteritis'), ('B54','Malaria, unspecified'),
    ('J06','Acute upper respiratory infection'), ('I10','Essential hypertension'),
    ('E86','Dehydration'), ('O26','Pregnancy-related care'), ('P07','Low birth weight'),
    ('E44','Malnutrition'), ('A90','Typhoid fever'), ('J45','Asthma')
]
HIGH_RISK = {'E44','P07','E86'}
MODERATE_RISK = {'A09','B54','A90'}
outcomes = ['Recovered','Referred','Admitted','Deceased']

def outcome_probabilities(diagnosis_code, age):
    extreme_age = age < 5 or age > 65
    if diagnosis_code in HIGH_RISK:
        return [0.35,0.25,0.30,0.10] if extreme_age else [0.50,0.25,0.20,0.05]
    elif diagnosis_code in MODERATE_RISK:
        return [0.60,0.22,0.14,0.04] if extreme_age else [0.70,0.18,0.10,0.02]
    else:
        return [0.78,0.14,0.06,0.02] if extreme_age else [0.85,0.10,0.04,0.01]

# ------------------------------------------------------------
# CLEAN pool: the 1,760 contract-validated visits.
# One row per visit (PRIMARY diagnosis only - fixes the earlier
# bug where a visit with 2 diagnoses was duplicated into 2 rows).
# ------------------------------------------------------------
primary_diag = diagnoses.drop_duplicates(subset='visit_id', keep='first')[['visit_id','diagnosis_code']]
primary_treat = treatments.drop_duplicates(subset='visit_id', keep='first')[['visit_id','outcome_status']]

clean = valid_visits.merge(primary_diag, on='visit_id').merge(primary_treat, on='visit_id')
clean['age'] = clean['patient_id'].map(age_lookup)
clean['age_imputed'] = False
clean = clean[['visit_id','age','age_imputed','visit_type','diagnosis_code','outcome_status']]
print(f"Clean pool: {len(clean)} rows")

# ------------------------------------------------------------
# DIRTY EXTRA pool: the 180 rejected records that still have a
# usable patient_id (invalid facility code / invalid visit_type /
# SLO breach). Their contract violation is in a metadata field
# (facility_id, visit_type, or timing), not directly in diagnosis
# or age. However, a clinic careless enough to submit a record
# with one of these errors is also realistically more likely to
# make an undetected error elsewhere on the same form, since
# sloppy data entry tends to co-occur rather than affect only the
# one field a contract rule happens to check. To model this
# honestly, 65% of these 180 records have their RECORDED diagnosis
# code deliberately mismatched from the diagnosis that actually
# produced the patient's true outcome, representing a plausible,
# undetected transcription error. The true outcome is generated
# from the real (hidden) diagnosis and age; the dirty model only
# ever sees the wrong, recorded diagnosis code as a feature.
# ------------------------------------------------------------
CORRUPTION_RATE = 0.65
usable_rejected = rejected[rejected['patient_id'].notna()].copy()
dirty_extra_rows = []
for _, r in usable_rejected.iterrows():
    age = age_lookup.get(r['patient_id'], GLOBAL_MEAN_AGE)
    true_code, _ = random.choice(diagnosis_options)
    probs = outcome_probabilities(true_code, age)
    outcome = random.choices(outcomes, weights=probs)[0]

    if random.random() < CORRUPTION_RATE:
        # Recorded (feature) diagnosis is wrong - a different code
        # from the one that actually produced this outcome
        other_codes = [c for c, _ in diagnosis_options if c != true_code]
        recorded_code = random.choice(other_codes)
    else:
        recorded_code = true_code

    dirty_extra_rows.append({'visit_id': r['visit_id'], 'age': age, 'age_imputed': False,
                              'visit_type': r['visit_type'], 'diagnosis_code': recorded_code,
                              'outcome_status': outcome})
dirty_usable = pd.DataFrame(dirty_extra_rows)
n_corrupted = int(len(usable_rejected) * CORRUPTION_RATE)
print(f"Dirty extra (usable violations): {len(dirty_usable)} rows, ~{n_corrupted} with a mismatched diagnosis code")

# ------------------------------------------------------------
# DIRTY MISSING-PATIENT pool: the 60 records with no patient_id at
# all. A real ("true") patient and age are assigned to generate a
# genuine outcome, but the FEATURE a naive pipeline would actually
# see has its age IMPUTED with the dataset-wide mean, since the
# broken patient link means the real age cannot be looked up. This
# is what actually injects realistic noise into a feature the model
# depends on, modelling exactly the kind of missing-data handling
# problem Nijman et al. (2022) document in real clinical ML studies.
# ------------------------------------------------------------
missing_patient = rejected[rejected['patient_id'].isna()].copy()
dirty_missing_rows = []
for _, r in missing_patient.iterrows():
    true_age = random.randint(0, 90)
    code, _ = random.choice(diagnosis_options)
    probs = outcome_probabilities(code, true_age)
    outcome = random.choices(outcomes, weights=probs)[0]
    dirty_missing_rows.append({'visit_id': r['visit_id'], 'age': GLOBAL_MEAN_AGE, 'age_imputed': True,
                                'visit_type': r['visit_type'], 'diagnosis_code': code, 'outcome_status': outcome})
dirty_missing = pd.DataFrame(dirty_missing_rows)
print(f"Dirty extra (missing patient link, age imputed): {len(dirty_missing)} rows")

dirty_extra_all = pd.concat([dirty_usable, dirty_missing], ignore_index=True)

clean.to_csv('ml_clean_pool.csv', index=False)
dirty_extra_all.to_csv('ml_dirty_extra_pool.csv', index=False)
print(f"\nTotal clean pool: {len(clean)} | Total dirty-extra pool: {len(dirty_extra_all)} | Combined would be: {len(clean)+len(dirty_extra_all)}")
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

RANDOM_STATE = 42

clean = pd.read_csv('ml_clean_pool.csv')
dirty_extra = pd.read_csv('ml_dirty_extra_pool.csv')

# ------------------------------------------------------------
# Held-out TEST set: 20% of the CLEAN pool only, set aside before
# anything else. Both models are judged on this same trustworthy
# set, so the comparison is fair - only the TRAINING data differs.
# ------------------------------------------------------------
clean_train, test_set = train_test_split(
    clean, test_size=0.20, random_state=RANDOM_STATE, stratify=clean['outcome_status']
)
print(f"Clean training rows: {len(clean_train)}")
print(f"Held-out test rows (clean, untouched by either model): {len(test_set)}")

# Model A: DIRTY - clean training portion PLUS the 240 unvalidated records
dirty_train = pd.concat([clean_train, dirty_extra], ignore_index=True)
print(f"Dirty training rows (clean portion + 240 unvalidated): {len(dirty_train)}")

features = ['age', 'visit_type', 'diagnosis_code']
target = 'outcome_status'

def build_pipeline(classifier):
    preprocess = ColumnTransformer([
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['visit_type', 'diagnosis_code']),
    ], remainder='passthrough')
    return Pipeline([('prep', preprocess), ('clf', classifier)])

MODELS = {
    'Decision Tree': DecisionTreeClassifier(max_depth=5, min_samples_leaf=10, random_state=RANDOM_STATE),
    'Logistic Regression': LogisticRegression(max_iter=1000, class_weight='balanced', random_state=RANDOM_STATE),
}

results = []
for model_name, classifier in MODELS.items():
    for data_name, train_df in [('Clean (contract-validated)', clean_train), ('Dirty (raw/unvalidated)', dirty_train)]:
        pipe = build_pipeline(classifier)
        X_train, y_train = train_df[features], train_df[target]
        X_test, y_test = test_set[features], test_set[target]
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)
        acc = accuracy_score(y_test, preds)
        f1w = f1_score(y_test, preds, average='weighted')
        f1m = f1_score(y_test, preds, average='macro')
        results.append({'algorithm': model_name, 'data': data_name, 'train_rows': len(train_df),
                         'accuracy': acc, 'weighted_f1': f1w, 'macro_f1': f1m})
        print(f"\n=== {model_name} | {data_name} (trained on {len(train_df)} rows) ===")
        print(classification_report(y_test, preds, zero_division=0))

# Majority-class baseline for context
baseline_pred = [test_set['outcome_status'].mode()[0]] * len(test_set)
baseline_acc = accuracy_score(test_set['outcome_status'], baseline_pred)
print(f"\nMajority-class baseline accuracy (always predict most common outcome): {baseline_acc:.3f}")

results_df = pd.DataFrame(results)
print("\n=== SUMMARY ===")
print(results_df.to_string(index=False))
results_df.to_csv('ml_experiment_results.csv', index=False)

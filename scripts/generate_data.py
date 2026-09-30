import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

# ------------------------------------------------------------
# Load real facilities (from extract_facilities.py output)
# ------------------------------------------------------------
fac = pd.read_csv('oyo_health_facilities.csv')
n_active = int(len(fac) * 0.5)
active_fac = fac.sample(n=n_active, random_state=42).reset_index(drop=True)
active_facility_ids = active_fac['facility_id'].tolist()
print(f"Total facilities: {len(fac)} | Active (50%): {len(active_facility_ids)}")

# ------------------------------------------------------------
# Realistic Nigerian names (Yoruba, Igbo, Hausa mix)
# ------------------------------------------------------------
male_first = ['Adewale','Emeka','Ibrahim','Oluwaseun','Chukwuemeka','Tunde','Musa','Femi',
              'Chidi','Abdullahi','Kayode','Uche','Yusuf','Segun','Nnamdi','Bashir','Damilare',
              'Obinna','Suleiman','Ayodele','Chibuzor','Kabiru','Wale','Ikechukwu','Aliyu']
female_first = ['Adaeze','Funmilayo','Aisha','Ngozi','Bisi','Fatima','Chiamaka','Folasade',
                'Amina','Ijeoma','Temitope','Halima','Chioma','Yetunde','Zainab','Blessing',
                'Omolara','Hadiza','Adaobi','Abimbola','Rukayat','Nkechi','Simisola','Maryam','Titilayo']
surnames = ['Okonkwo','Adeyemi','Mohammed','Eze','Balogun','Abubakar','Nwosu','Ogundipe',
            'Ibrahim','Chukwu','Afolabi','Suleiman','Okafor','Ajayi','Yakubu','Nnamdi',
            'Adebayo','Uzoma','Aliyu','Okeke','Bello','Ogunleye','Chinedu','Salihu','Fashola',
            'Onyeka','Lawal','Emeka','Sanni','Obi']

def random_name():
    if random.random() < 0.5:
        first = random.choice(male_first); sex = 'M'
    else:
        first = random.choice(female_first); sex = 'F'
    return f"{first} {random.choice(surnames)}", sex

# ------------------------------------------------------------
# 1. DEPARTMENTS (~1-3 per active facility)
# ------------------------------------------------------------
dept_options = ['General Outpatient','Maternity','Pediatrics','Antenatal Care',
                'Immunization','Pharmacy','Laboratory']
departments = []
dept_id = 1
for fid in active_facility_ids:
    n_dept = random.choice([1,1,2,2,3])
    chosen = random.sample(dept_options, min(n_dept, len(dept_options)))
    for d in chosen:
        departments.append({'department_id': dept_id, 'facility_id': fid, 'department_name': d})
        dept_id += 1
departments = pd.DataFrame(departments)
print("Departments:", len(departments))

# ------------------------------------------------------------
# 2. STAFF (~2 per department)
# ------------------------------------------------------------
roles = ['Doctor','Nurse','Lab Technician','Records Officer']
role_weights = [0.25,0.45,0.15,0.15]
staff = []
staff_id = 1
for _, row in departments.iterrows():
    for _ in range(random.choice([1,2,2,3])):
        name, _ = random_name()
        role = random.choices(roles, weights=role_weights)[0]
        staff.append({'staff_id': staff_id, 'department_id': row['department_id'],
                      'full_name': name, 'role': role})
        staff_id += 1
staff = pd.DataFrame(staff)
print("Staff:", len(staff))

# ------------------------------------------------------------
# 3. PATIENTS (~1500)
# ------------------------------------------------------------
N_PATIENTS = 1500
patients = []
for pid in range(1, N_PATIENTS+1):
    name, sex = random_name()
    age_years = random.randint(0, 90)
    dob = (datetime(2026,1,1) - timedelta(days=age_years*365 + random.randint(0,364))).date()
    patients.append({'patient_id': pid, 'full_name': name, 'sex': sex, 'date_of_birth': dob, 'age': age_years})
patients = pd.DataFrame(patients)
print("Patients:", len(patients))

# ------------------------------------------------------------
# 4. APPOINTMENTS (~800)
# ------------------------------------------------------------
N_APPT = 800
statuses = ['Scheduled','Completed','No-show','Cancelled']
status_w = [0.15,0.65,0.12,0.08]
appointments = []
for aid in range(1, N_APPT+1):
    pid = random.randint(1, N_PATIENTS)
    dept_row = departments.sample(1).iloc[0]
    sched_date = datetime(2026,1,1) + timedelta(days=random.randint(0,240))
    appointments.append({'appointment_id': aid, 'patient_id': pid,
                          'department_id': dept_row['department_id'],
                          'scheduled_date': sched_date.date(),
                          'status': random.choices(statuses, weights=status_w)[0]})
appointments = pd.DataFrame(appointments)
print("Appointments:", len(appointments))

# ------------------------------------------------------------
# 5. RAW INCOMING VISITS (~2000) - includes deliberate contract violations
# ------------------------------------------------------------
N_VISITS = 2000
visit_types = ['Outpatient','Inpatient','Emergency','Follow-up']
raw_visits = []
dept_by_facility = departments.groupby('facility_id')
staff_by_dept = staff.groupby('department_id')

for vid in range(1, N_VISITS+1):
    fid = random.choice(active_facility_ids)
    dept_candidates = dept_by_facility.get_group(fid) if fid in dept_by_facility.groups else departments.sample(1)
    dept_row = dept_candidates.sample(1).iloc[0]
    staff_candidates = staff_by_dept.get_group(dept_row['department_id']) if dept_row['department_id'] in staff_by_dept.groups else staff.sample(1)
    staff_row = staff_candidates.sample(1).iloc[0]
    pid = random.randint(1, N_PATIENTS)
    appointment_id = random.choice([None]*6 + list(appointments[appointments['department_id']==dept_row['department_id']]['appointment_id']) or [None])

    visit_date = datetime(2026,1,1) + timedelta(days=random.randint(0,240), hours=random.randint(0,23))
    delay_hours = random.choice([1,2,3,4,5,6,8,12,20])
    record_created_at = visit_date + timedelta(hours=delay_hours)

    row = {
        'visit_id': vid, 'patient_id': pid, 'facility_id': fid,
        'department_id': dept_row['department_id'], 'attending_staff_id': staff_row['staff_id'],
        'appointment_id': appointment_id, 'visit_date': visit_date,
        'record_created_at': record_created_at, 'visit_type': random.choice(visit_types),
    }
    raw_visits.append(row)

raw_visits = pd.DataFrame(raw_visits)

# ---- Inject 12% deliberate contract violations (unchanged from before) ----
VIOLATION_RATE = 0.415  # 830 of 2,000, per the revised experimental design
n_violations = int(N_VISITS * VIOLATION_RATE)
violation_idx = np.random.choice(raw_visits.index, n_violations, replace=False)
for i, idx in enumerate(violation_idx):
    v_type = i % 4
    if v_type == 0:
        raw_visits.loc[idx, 'patient_id'] = None
    elif v_type == 1:
        raw_visits.loc[idx, 'record_created_at'] = raw_visits.loc[idx,'visit_date'] + timedelta(hours=random.randint(30,96))
    elif v_type == 2:
        raw_visits.loc[idx, 'facility_id'] = 'FAC9999'
    else:
        raw_visits.loc[idx, 'visit_type'] = 'Unknown'

raw_visits.to_csv('incoming_visits_raw.csv', index=False)
print("Raw incoming visits (with violations):", len(raw_visits), "| Violations injected:", n_violations)

# ------------------------------------------------------------
# 6. DIAGNOSES (unchanged logic) and TREATMENTS (NEW realistic outcome logic)
# ------------------------------------------------------------
diagnosis_options = [
    ('A09','Diarrhoea and gastroenteritis'), ('B54','Malaria, unspecified'),
    ('J06','Acute upper respiratory infection'), ('I10','Essential hypertension'),
    ('E86','Dehydration'), ('O26','Pregnancy-related care'), ('P07','Low birth weight'),
    ('E44','Malnutrition'), ('A90','Typhoid fever'), ('J45','Asthma')
]
treatment_options = ['Medication - Antimalarial','Medication - Antibiotic','Oral Rehydration Therapy',
                     'Wound Dressing','Immunization','Referral','Antenatal Checkup','Nutritional Supplement']
outcomes = ['Recovered','Referred','Admitted','Deceased']

# --- NEW: diagnosis risk categories, used to make outcome_status realistic ---
HIGH_RISK = {'E44', 'P07', 'E86'}       # malnutrition, low birth weight, dehydration
MODERATE_RISK = {'A09', 'B54', 'A90'}   # diarrhoea, malaria, typhoid
LOW_RISK = {'J06', 'I10', 'O26', 'J45'} # respiratory infection, hypertension, pregnancy care, asthma

def outcome_probabilities(diagnosis_code, age, ownership='Public', visit_type='Outpatient'):
    """Returns realistic outcome_status probabilities based on diagnosis, age,
    facility ownership, and visit type. Ownership and visit type have smaller,
    secondary effects, reflecting realistic resourcing and acuity differences,
    and are what make the ML data-quality experiment meaningful: an invalid
    facility_code or visit_type removes exactly this information."""
    extreme_age = age < 5 or age > 65
    if diagnosis_code in HIGH_RISK:
        if extreme_age:
            base = [0.35, 0.25, 0.30, 0.10]
        else:
            base = [0.50, 0.25, 0.20, 0.05]
    elif diagnosis_code in MODERATE_RISK:
        if extreme_age:
            base = [0.60, 0.22, 0.14, 0.04]
        else:
            base = [0.70, 0.18, 0.10, 0.02]
    else:
        if extreme_age:
            base = [0.78, 0.14, 0.06, 0.02]
        else:
            base = [0.85, 0.10, 0.04, 0.01]

    # Secondary effect: private facilities skew marginally better outcomes
    if ownership == 'Private':
        base = [base[0] + 0.05, base[1] - 0.02, base[2] - 0.02, base[3] - 0.01]
    # Secondary effect: Emergency visits skew marginally more severe
    if visit_type == 'Emergency':
        base = [base[0] - 0.04, base[1] + 0.01, base[2] + 0.02, base[3] + 0.01]

    base = [max(0.01, p) for p in base]
    total = sum(base)
    return [p / total for p in base]

diagnoses = []
treatments = []
diag_id = 1
treat_id = 1
clean_visits = raw_visits.dropna(subset=['patient_id']).copy()
patient_age_lookup = dict(zip(patients['patient_id'], patients['age']))
facility_ownership_lookup = dict(zip(fac['facility_id'], fac['ownership']))

for _, v in clean_visits.iterrows():
    patient_age = patient_age_lookup.get(v['patient_id'], 30)
    ownership = facility_ownership_lookup.get(v['facility_id'], 'Unknown')  # 'Unknown' when facility_id is invalid

    primary_code, primary_desc = random.choice(diagnosis_options)
    diagnoses.append({'diagnosis_id': diag_id, 'visit_id': v['visit_id'],
                      'diagnosis_code': primary_code, 'diagnosis_description': primary_desc})
    diag_id += 1
    if random.random() < 0.25:
        code2, desc2 = random.choice(diagnosis_options)
        diagnoses.append({'diagnosis_id': diag_id, 'visit_id': v['visit_id'],
                          'diagnosis_code': code2, 'diagnosis_description': desc2})
        diag_id += 1

    probs = outcome_probabilities(primary_code, patient_age, ownership, v['visit_type'])
    visit_outcome = random.choices(outcomes, weights=probs)[0]

    for _ in range(random.choice([1,1,1,2])):
        treatments.append({'treatment_id': treat_id, 'visit_id': v['visit_id'],
                           'administered_by_staff_id': v['attending_staff_id'],
                           'treatment_type': random.choice(treatment_options),
                           'treatment_description': 'As administered during visit',
                           'outcome_status': visit_outcome})
        treat_id += 1

diagnoses = pd.DataFrame(diagnoses)
treatments = pd.DataFrame(treatments)
print("Diagnoses (all patient-id-present visits):", len(diagnoses), "| Treatments:", len(treatments))
print("\nOutcome distribution (before contract filtering):")
print(treatments['outcome_status'].value_counts())

# Save UNFILTERED versions first (needed later for the ML "dirty data" experiment,
# since these still include the facility/visit-type contract violations)
diagnoses.to_csv('diagnoses_all.csv', index=False)
treatments.to_csv('treatments_all.csv', index=False)

# ------------------------------------------------------------
# Save all tables
# ------------------------------------------------------------
departments.to_csv('departments.csv', index=False)
staff.to_csv('staff.csv', index=False)
patients.drop(columns=['age']).to_csv('patients.csv', index=False)  # age was a helper column only
appointments.to_csv('appointments.csv', index=False)
diagnoses.to_csv('diagnoses.csv', index=False)
treatments.to_csv('treatments.csv', index=False)

print("\nAll files saved.")

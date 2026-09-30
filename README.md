# Data Engineering and Data Contracts

**Author:** Fagbenjo Samson Akinyele (Matriculation Number: 261743)
**Course:** CSC 796 Advanced Data Engineering, University of Ibadan (2025/2026 Session)
**Lecturer:** Dr. B. I. Ayinla
**Topic:** Data Engineering and Data Contracts, a Case Study of a Health Management Information System (HMIS) in Oyo State, Nigeria

## What this repository contains

This repository holds the source code referenced in the accompanying term paper. It is linked from the paper via a QR code in the appendix, since the full code was not included inline in the written document.

| File | Purpose |
|---|---|
| `facilities.py` | The Python script used to reduce the national GRID3 dataset (51,022 rows, 21 attributes) down to the Oyo State facilities reference table (2,045 rows, 11 attributes), via selection (filtering to Oyo State) and projection (keeping only the relevant columns), and to generate the clean `facility_id` surrogate key. |
| `hmis_data_contract_query.sql` | The PostgreSQL Data Definition Language (DDL) used to create the 8-table HMIS database schema, including primary keys, foreign keys, and CHECK constraints. |
| `generate_data.py` | The Python script used to generate the simulated departments, staff, patients, appointments, and raw incoming visit records (including deliberately injected contract violations). |
| `validate_contract.py` | The Python validation routine that checks every incoming visit record against the data contract's schema and SLO rules, splitting records into `visits_valid.csv` (accepted) and `rejected_records_log.csv` (rejected, with reasons). |

## Data sources

- **Real data:** GRID3 Nigeria Health Facilities dataset (v2.0), obtained from the Humanitarian Data Exchange, filtered to Oyo State.
- **Simulated data:** Patients, staff, departments, appointments, and visit records, generated specifically for this study.

## How to run this code

1. Run `facilities.py` to reduce the national GRID3 dataset down to the Oyo State facilities reference table.
2. Run `hmis_data_contract_query.sql` in PostgreSQL (via pgAdmin's Query Tool or `psql`) to create the database tables.
3. Run `generate_data.py` in a Python environment with `pandas` and `numpy` installed to produce the simulated CSV files.
4. Run `validate_contract.py` to validate the generated visit records against the data contract, producing the accepted and rejected output files.
5. Import the resulting CSV files into the corresponding PostgreSQL tables using pgAdmin's Import/Export Data tool.

## Note on data privacy

No real patient data was used anywhere in this project. Patient, staff, and visit records were entirely simulated to avoid any real individual's health information being used, in line with standard ethical practice for student research projects of this kind.

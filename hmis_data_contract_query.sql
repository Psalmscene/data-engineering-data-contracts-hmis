CREATE TABLE facilities (
    facility_id             VARCHAR(10)   PRIMARY KEY,
    nhfr_facility_code_raw  VARCHAR(30),
    facility_name           VARCHAR(150)  NOT NULL,
    lga                     VARCHAR(80)   NOT NULL,
    ward                    VARCHAR(80),
    ownership               VARCHAR(20),
    ownership_type          VARCHAR(40),
    facility_level          VARCHAR(20),
    facility_level_option   VARCHAR(60),
    latitude                DECIMAL(9,6),
    longitude               DECIMAL(9,6)
);

CREATE TABLE departments (
    department_id     SERIAL PRIMARY KEY,
    facility_id        VARCHAR(10) NOT NULL REFERENCES facilities(facility_id),
    department_name    VARCHAR(80) NOT NULL
);

CREATE TABLE staff (
    staff_id        SERIAL PRIMARY KEY,
    department_id   INT NOT NULL REFERENCES departments(department_id),
    full_name       VARCHAR(100) NOT NULL,
    role            VARCHAR(30) NOT NULL CHECK (role IN ('Doctor','Nurse','Lab Technician','Records Officer'))
);

CREATE TABLE patients (
    patient_id      SERIAL PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    sex             CHAR(1) NOT NULL CHECK (sex IN ('M','F')),
    date_of_birth   DATE NOT NULL
);

CREATE TABLE appointments (
    appointment_id   SERIAL PRIMARY KEY,
    patient_id       INT NOT NULL REFERENCES patients(patient_id),
    department_id    INT NOT NULL REFERENCES departments(department_id),
    scheduled_date   DATE NOT NULL,
    status           VARCHAR(20) NOT NULL CHECK (status IN ('Scheduled','Completed','No-show','Cancelled'))
);

CREATE TABLE visits (
    visit_id            SERIAL PRIMARY KEY,
    patient_id          INT NOT NULL REFERENCES patients(patient_id),
    facility_id         VARCHAR(10) NOT NULL REFERENCES facilities(facility_id),
    department_id       INT NOT NULL REFERENCES departments(department_id),
    attending_staff_id  INT NOT NULL REFERENCES staff(staff_id),
    appointment_id      INT REFERENCES appointments(appointment_id),
    visit_date          TIMESTAMP NOT NULL,
    record_created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    visit_type          VARCHAR(20) NOT NULL CHECK (visit_type IN ('Outpatient','Inpatient','Emergency','Follow-up'))
);

CREATE TABLE diagnoses (
    diagnosis_id          SERIAL PRIMARY KEY,
    visit_id              INT NOT NULL REFERENCES visits(visit_id),
    diagnosis_code        VARCHAR(10) NOT NULL,
    diagnosis_description VARCHAR(200)
);

CREATE TABLE treatments (
    treatment_id            SERIAL PRIMARY KEY,
    visit_id                INT NOT NULL REFERENCES visits(visit_id),
    administered_by_staff_id INT NOT NULL REFERENCES staff(staff_id),
    treatment_type          VARCHAR(40) NOT NULL,
    treatment_description   VARCHAR(200),
    outcome_status          VARCHAR(20) NOT NULL CHECK (outcome_status IN ('Recovered','Referred','Admitted','Deceased'))
);

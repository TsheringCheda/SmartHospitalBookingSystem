CREATE TABLE medical_records (

    record_id INT AUTO_INCREMENT PRIMARY KEY,

    appointment_id INT,

    patient_id INT,

    doctor_id INT,

    diagnosis TEXT,

    prescription TEXT,

    doctor_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
    REFERENCES appointments(appointment_id),

    FOREIGN KEY (patient_id)
    REFERENCES patients(patient_id),

    FOREIGN KEY (doctor_id)
    REFERENCES doctors(doctor_id)

);
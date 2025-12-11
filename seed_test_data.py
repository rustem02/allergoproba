import os

import psycopg2
from psycopg2.extras import execute_values
import json


DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ==============================
# test data
# ==============================

patients = [
    ("900101300001", "Ivanov Ivan Ivanovich",       "+7 701 111 11 11", "1990-01-01", 100000001),
    ("910202300002", "Petrova Anna Sergeevna",      "+7 701 222 22 22", "1991-02-02", 100000002),
    ("920303300003", "Sidorov Pavel Olegovich",     "+7 701 333 33 33", "1992-03-03", 100000003),
    ("930404300004", "Kim Aigerim Erbolovna",       "+7 701 444 44 44", "1993-04-04", 100000004),
    ("940505300005", "Zhumagulov Daniyar Nurlan",   "+7 701 555 55 55", "1994-05-05", 100000005),
    ("950606300006", "Smirnova Olga Petrovna",      "+7 701 666 66 66", "1995-06-06", 100000006),
    ("960707300007", "Tuleuov Marat Serikovich",    "+7 701 777 77 77", "1996-07-07", 100000007),
    ("970808300008", "Abdullina Madina Rustemovna", "+7 701 888 88 88", "1997-08-08", 100000008),
    ("980909300009", "Kuznetsov Alexey Viktorovich","+7 701 999 99 99", "1998-09-09", 100000009),
    ("990101300010", "Beketova Aida Kuanyshovna",   "+7 747 123 45 67", "1999-01-10", 100000010),
]

orders = [
    ("98711", "sent_to_telegram", "DentLux",     "Ivanov I.I.",  "Basic",
     ["Lidocaine"],                        None),   # results

    ("98712", "sent_to_telegram", "DentLux",     "Ivanov I.I.",  "Extended",
     ["Lidocaine", "Articaine"],          None),

    ("98713", "blood_taken",      "SmileClinic","Petrova A.A.", "Basic",
     ["Articaine"],                      None),

    ("98714", "blood_taken",      "SmileClinic","Petrova A.A.", "VIP",
     ["Lidocaine","Mepivacaine"],        None),

    ("98715", "results_ready",    "CityDent",   "Sidorov S.S.", "Basic",
     ["Mepivacaine"],                    {"Mepivacaine": "Negative"}),

    ("98716", "results_ready",    "CityDent",   "Sidorov S.S.", "Extended",
     ["Lidocaine","Articaine","Mepivacaine"],
     {"Lidocaine":"Negative","Articaine":"Positive","Mepivacaine":"Negative"}),

    ("98717", "sent_to_telegram", "HappySmile", "Kim K.K.",     "Basic",
     ["Articaine","Mepivacaine"],        None),

    ("98718", "blood_taken",      "HappySmile", "Kim K.K.",     "Extended",
     ["Lidocaine"],                      None),

]

# ==============================
# mock generate qr
# ==============================
QR_FAKE = "data:image/png;base64,TEST"



def seed_data():
    conn = psycopg2.connect(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id               SERIAL PRIMARY KEY,
        iin              VARCHAR(12) NOT NULL UNIQUE,
        full_name        TEXT        NOT NULL,
        phone_whatsapp   TEXT        NOT NULL,
        date_of_birth    DATE        NOT NULL,
        telegram_chat_id BIGINT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id           SERIAL PRIMARY KEY,
        code         VARCHAR(10) NOT NULL UNIQUE,
        status       TEXT        NOT NULL,
        clinic_name  TEXT        NOT NULL,
        doctor_name  TEXT        NOT NULL,
        tariff       TEXT        NOT NULL,
        allergens    JSONB       NOT NULL,
        patient_id   INT         NOT NULL REFERENCES patients(id),
        qr_data_url  TEXT        NOT NULL,
        results      JSONB
    );
    """)

    conn.commit()

    execute_values(cur,
        """
        INSERT INTO patients (iin, full_name, phone_whatsapp, date_of_birth, telegram_chat_id)
        VALUES %s
        ON CONFLICT (iin) DO NOTHING
        """,
        patients
    )
    conn.commit()


    cur.execute("SELECT id, iin FROM patients ORDER BY id;")
    rows = cur.fetchall()
    patient_map = {row[1]: row[0] for row in rows}

    order_rows = []
    for idx, o in enumerate(orders):
        code, status, clinic, doctor, tariff, allergen_list, results = o
        patient_id = rows[idx][0]  # 1 → 1, 2 → 2 ... 10 → 10

        order_rows.append((
            code,
            status,
            clinic,
            doctor,
            tariff,
            json.dumps(allergen_list),
            patient_id,
            QR_FAKE,
            json.dumps(results) if results else None,
        ))

    execute_values(cur,
        """
        INSERT INTO orders
        (code, status, clinic_name, doctor_name, tariff, allergens, patient_id, qr_data_url, results)
        VALUES %s
        ON CONFLICT (code) DO NOTHING
        """,
        order_rows
    )
    conn.commit()

    cur.close()
    conn.close()

    print("test data seeded.")


if __name__ == "__main__":
    seed_data()

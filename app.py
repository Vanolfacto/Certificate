from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import hashlib
from datetime import datetime
from reportlab.pdfgen import canvas
import io

app=Flask(__name__)
DB_NAME='sertifikati.db'

def init_db():
    conn=sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sertifikati(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              student_ime TEXT NOT NULL,
              kurs TEXT NOT NULL,
              datum TEXT NOT NULL,
              prethodni_hash TEXT,
              hash TEXT NOT NULL
              )
    ''')
    conn.commit()
    conn.close()

def generate_hash(student_ime, kurs, datum, prethodni_hash):
    data = f"{student_ime}{kurs}{datum}{prethodni_hash}"
    return hashlib.sha256(data.encode()).hexdigest()

def proveri_integritet():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM sertifikati ORDER BY id")
    sertifikati = c.fetchall()
    conn.close()

    prethodni_hash = '0'
    for s in sertifikati:
        id, student_ime, kurs, datum, prethodni_hash_baza, hash_baza = s
        izracunati_hash = generate_hash(student_ime, kurs, datum, prethodni_hash)
        if izracunati_hash != hash_baza or prethodni_hash_baza != prethodni_hash:
            return False  # Neispravno
        prethodni_hash = hash_baza

    return True  # Sve ok
@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM sertifikati")
    sertifikati = c.fetchall()
    conn.close()
    return render_template("index.html", sertifikati=sertifikati)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        student_ime = request.form['student_ime']
        kurs = request.form['kurs']
        datum = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT hash FROM sertifikati ORDER BY id DESC LIMIT 1")
        last = c.fetchone()
        prethodni_hash = last[0] if last else '0'

        novi_hash = generate_hash(student_ime, kurs, datum, prethodni_hash)

        c.execute("INSERT INTO sertifikati (student_ime, kurs, datum, prethodni_hash, hash) VALUES (?, ?, ?, ?, ?)",
                  (student_ime, kurs, datum, prethodni_hash, novi_hash))
        conn.commit()
        conn.close()

        return redirect('/')
    return render_template("add.html")

#  PDF GENERACIJA
@app.route('/generate_pdf/<int:id>')
def generate_pdf(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT student_ime, kurs, datum FROM sertifikati WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return "Sertifikat nije pronađen."

    student_ime, kurs, datum = row

    # Kreiraj PDF u memoriji
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(100, 750, "SERTIFIKAT O ZAVRŠENOM KURSU")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 700, f"Ime studenta: {student_ime}")
    pdf.drawString(100, 680, f"Kurs: {kurs}")
    pdf.drawString(100, 660, f"Datum izdavanja: {datum}")
    pdf.drawString(100, 620, "Cestitamo na uspešnom završetku!")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="sertifikat.pdf", mimetype='application/pdf')

@app.route('/provera')
def provera():
    valid = proveri_integritet()
    status = "ISPRAVAN ✅" if valid else "NEISPRAVAN ❌"
    color = "green" if valid else "red"
    return f"""
    <div style="font-family: Arial, sans-serif; font-size: 1.5em; color: {color}; 
                background-color: #f0f0f0; padding: 20px; border-radius: 10px; 
                width: fit-content; margin: 30px auto; text-align: center; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
        Integritet lanca: <strong>{status}</strong>
    </div>
    <div style="text-align: center; margin-top: 15px;">
        <a href='/' style="text-decoration: none; color: #007BFF;">Nazad</a>
    </div>
"""

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
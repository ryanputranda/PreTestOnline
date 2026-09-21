import os
from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)
app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "127.0.0.1")
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER", "root")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "")
app.config["MYSQL_DB"] = os.getenv("MYSQL_DB", "ukdc_exam")
app.config["MYSQL_PORT"] = int(os.getenv("MYSQL_PORT", "3306"))
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)

questions = [
    ("Apa kepanjangan dari CPU?", "Central Processing Unit", "Computer Personal Unit", "Central Program Utility", "Computer Processing User", "A", 1),
    ("Bahasa yang digunakan untuk membuat halaman web di sisi struktur adalah?", "Python", "HTML", "SQL", "C++", "B", 2),
    ("Manakah yang termasuk sistem operasi?", "MySQL", "Linux", "HTML", "Git", "B", 3),
    ("Apa fungsi utama database?", "Mengedit gambar", "Menyimpan dan mengelola data", "Membuat desain logo", "Memutar video", "B", 4),
    ("HTTP merupakan protokol yang umum digunakan untuk?", "Komunikasi web", "Kompresi file", "Pemrosesan gambar", "Mengatur BIOS", "A", 5),
]

with app.app_context():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM questions")
    if cur.fetchone()["total"] == 0:
        cur.executemany("""
            INSERT INTO questions
            (question_text, option_a, option_b, option_c, option_d, correct_answer, question_order)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, questions)
        mysql.connection.commit()
        print("Sample questions inserted.")
    else:
        print("Questions already exist; seed skipped.")
    cur.close()

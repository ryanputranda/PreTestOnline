import io, os, secrets
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for, send_file, g
from openpyxl import Workbook
from werkzeug.security import check_password_hash, generate_password_hash

import os

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "ukdc_exam"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "charset": "utf8mb4",
    "cursorclass": __import__("pymysql").cursors.DictCursor,
    "autocommit": False,
}


@app.before_request
def open_db():
    if "db" not in g:
        import pymysql
        g.db = pymysql.connect(**MYSQL_CONFIG)


@app.teardown_appcontext
def close_db(exception=None):
    connection = g.pop("db", None)
    if connection is not None:
        if exception is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        connection.close()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def db():
    return g.db

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped

def get_questions():
    cur = db().cursor()
    cur.execute("""
        SELECT id, question_text, option_a, option_b, option_c, option_d
        FROM questions
        ORDER BY question_order ASC, id ASC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def get_question(qid):
    cur = db().cursor()
    cur.execute("SELECT * FROM questions WHERE id=%s", (qid,))
    row = cur.fetchone()
    cur.close()
    return row

@app.post("/admin/results/delete-all")
@admin_required
def delete_all_results():
    cur = db().cursor()

    try:
        cur.execute("DELETE FROM results")
        db().commit()

        flash("Semua hasil peserta berhasil dihapus.", "success")

    except Exception:
        db().rollback()
        flash("Gagal menghapus semua hasil peserta.", "error")

    finally:
        cur.close()

    return redirect(url_for("admin_results"))



@app.route("/")
def home():
    return render_template("home.html")

@app.post("/start")
def start():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Nama lengkap wajib diisi.", "error")
        return redirect(url_for("home"))

    questions = get_questions()
    if not questions:
        flash("Belum ada soal yang tersedia.", "error")
        return redirect(url_for("home"))

    session["exam"] = {
        "name": name,
        "question_ids": [q["id"] for q in questions],
        "answers": {},
        "started_at": datetime.now().isoformat()
    }
    return redirect(url_for("exam", number=1))

@app.route("/exam/<int:number>", methods=["GET", "POST"])
def exam(number):
    exam_state = session.get("exam")
    if not exam_state:
        return redirect(url_for("home"))

    ids = exam_state["question_ids"]
    total = len(ids)
    if number < 1 or number > total:
        return redirect(url_for("exam", number=1))

    qid = ids[number - 1]
    question = get_question(qid)
    if not question:
        return redirect(url_for("home"))

    if request.method == "POST":
        answer = request.form.get("answer", "").upper()
        if answer not in ("A", "B", "C", "D"):
            flash("Silakan pilih salah satu jawaban.", "error")
            return render_template("exam.html", question=question, number=number,
                                   total=total, selected=None,
                                   is_last=(number == total))
        exam_state["answers"][str(qid)] = answer
        session["exam"] = exam_state

        if number == total:
            return redirect(url_for("confirm_finish"))
        return redirect(url_for("exam", number=number + 1))

    selected = exam_state["answers"].get(str(qid))
    return render_template("exam.html", question=question, number=number,
                           total=total, selected=selected,
                           is_last=(number == total))

@app.post("/exam/<int:number>/back")
def exam_back(number):
    exam_state = session.get("exam")
    if not exam_state:
        return redirect(url_for("home"))
    answer = request.form.get("answer", "").upper()
    if answer in ("A", "B", "C", "D"):
        ids = exam_state["question_ids"]
        qid = ids[number - 1]
        exam_state["answers"][str(qid)] = answer
        session["exam"] = exam_state
    return redirect(url_for("exam", number=max(1, number - 1)))

@app.route("/confirm-finish", methods=["GET", "POST"])
def confirm_finish():
    exam_state = session.get("exam")
    if not exam_state:
        return redirect(url_for("home"))
    if request.method == "POST":
        return finish_exam()
    return render_template("confirm.html")

def finish_exam():
    exam_state = session.get("exam")
    ids = exam_state["question_ids"]
    answers = exam_state["answers"]

    cur = db().cursor()
    correct = 0
    review = []

    for qid in ids:
        cur.execute("SELECT * FROM questions WHERE id=%s", (qid,))
        q = cur.fetchone()
        given = answers.get(str(qid))
        is_correct = given == q["correct_answer"]
        if is_correct:
            correct += 1
        review.append({
            "question": q["question_text"],
            "given": given or "-",
            "correct": q["correct_answer"],
            "status": is_correct
        })

    total = len(ids)
    wrong = total - correct
    score = round((correct / total) * 100, 2) if total else 0

    cur.execute("""
        INSERT INTO results
        (participant_name, test_date, total_questions, correct_answers, incorrect_answers, final_score)
        VALUES (%s, NOW(), %s, %s, %s, %s)
    """, (exam_state["name"], total, correct, wrong, score))
    db().commit()
    cur.close()

    result = {
        "name": exam_state["name"],
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "score": score,
        "review": review
    }
    session.pop("exam", None)
    return render_template("result.html", result=result)

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_questions"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_questions"))
        flash("Username atau password salah.", "error")
    return render_template("admin/login.html")

@app.post("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/questions")
@admin_required
def admin_questions():
    cur = db().cursor()
    cur.execute("SELECT * FROM questions ORDER BY question_order ASC, id ASC")
    questions = cur.fetchall()
    cur.close()
    return render_template("admin/questions.html", questions=questions)

@app.route("/admin/questions/new", methods=["GET", "POST"])
@admin_required
def admin_new_question():
    if request.method == "POST":
        data = request.form
        try:
            order = int(data.get("question_order") or 0)
        except ValueError:
            order = 0
        if not data.get("question_text", "").strip():
            flash("Teks soal wajib diisi.", "error")
            return render_template("admin/question_form.html", question=None)
        cur = db().cursor()
        cur.execute("""
            INSERT INTO questions
            (question_text, option_a, option_b, option_c, option_d, correct_answer, question_order)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (data["question_text"].strip(), data["option_a"].strip(),
              data["option_b"].strip(), data["option_c"].strip(),
              data["option_d"].strip(), data["correct_answer"], order))
        db().commit()
        cur.close()
        flash("Soal berhasil ditambahkan.", "success")
        return redirect(url_for("admin_questions"))
    return render_template("admin/question_form.html", question=None)

@app.route("/admin/questions/<int:qid>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_question(qid):
    question = get_question(qid)
    if not question:
        return "Soal tidak ditemukan", 404

    if request.method == "POST":
        data = request.form
        try:
            order = int(data.get("question_order") or 0)
        except ValueError:
            order = 0
        cur = db().cursor()
        cur.execute("""
            UPDATE questions SET question_text=%s, option_a=%s, option_b=%s,
            option_c=%s, option_d=%s, correct_answer=%s, question_order=%s
            WHERE id=%s
        """, (data["question_text"].strip(), data["option_a"].strip(),
              data["option_b"].strip(), data["option_c"].strip(),
              data["option_d"].strip(), data["correct_answer"], order, qid))
        db().commit()
        cur.close()
        flash("Soal berhasil diperbarui.", "success")
        return redirect(url_for("admin_questions"))
    return render_template("admin/question_form.html", question=question)

@app.post("/admin/questions/<int:qid>/delete")
@admin_required
def admin_delete_question(qid):
    cur = db().cursor()
    cur.execute("DELETE FROM questions WHERE id=%s", (qid,))
    db().commit()
    cur.close()
    flash("Soal berhasil dihapus.", "success")
    return redirect(url_for("admin_questions"))

@app.post("/admin/results/delete/<int:result_id>")
@admin_required
def delete_result(result_id):
    cur = db().cursor()
    try:
        cur.execute("DELETE FROM results WHERE id=%s", (result_id,))
        db().commit()
        flash("Hasil peserta berhasil dihapus.", "success")
    except Exception:
        db().rollback()
        flash("Gagal menghapus hasil peserta.", "error")
    finally:
        cur.close()

    return redirect(url_for("admin_results"))


@app.route("/admin/results")
@admin_required
def admin_results():
    sort = request.args.get("sort", "date")
    order = "test_date DESC"
    if sort == "score":
        order = "final_score DESC, test_date DESC"
    elif sort == "name":
        order = "participant_name ASC, test_date DESC"

    cur = db().cursor()
    cur.execute(f"SELECT * FROM results ORDER BY {order}")
    results = cur.fetchall()
    cur.close()
    return render_template("admin/results.html", results=results, sort=sort)

@app.get("/admin/results/export")
@admin_required
def export_results():
    cur = db().cursor()
    cur.execute("""
        SELECT participant_name, test_date, total_questions,
               correct_answers, incorrect_answers, final_score
        FROM results ORDER BY test_date DESC
    """)
    rows = cur.fetchall()
    cur.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Hasil Tes"
    headers = ["No", "Nama Peserta", "Tanggal Tes", "Jumlah Soal",
               "Jawaban Benar", "Jawaban Salah", "Nilai"]
    ws.append(headers)

    for i, row in enumerate(rows, 1):
        ws.append([i, row["participant_name"], row["test_date"],
                   row["total_questions"], row["correct_answers"],
                   row["incorrect_answers"], row["final_score"]])

    widths = [8, 30, 22, 15, 17, 16, 12]
    for idx, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + idx)].width = width
    ws.freeze_panes = "A2"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name="hasil_tes_ilmu_informatika.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)

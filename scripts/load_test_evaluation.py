"""Run disposable, local 60-student pretest and evaluation flow load tests.

This script creates a temporary SQLite database and a private Flask server on
127.0.0.1. It never connects to the database configured in .env and deletes its
temporary database when the run ends.
"""

import os
import logging
import json
import re
import statistics
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


TEMP_DIR = tempfile.TemporaryDirectory(prefix="edudaya-load-test-")
DB_PATH = Path(TEMP_DIR.name) / "load-test.sqlite3"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"

from werkzeug.serving import make_server
import requests

from app import app, db
from app.model import ActivityLog, Classes, EvaluationResult, PretestResult, Score, User


STUDENTS = 60
PASSWORD = "Edudaya-Load-Test-Only-2026!"
ANSWERS = {
    "1": "trapesium",
    "2": "layang-layang",
    "3": "60 cm2",
    "4": "60 cm",
    "5": "12 cm2",
    "6": "Bangun A",
    "7": "Salah karena 2 x (p+l) adalah rumus keliling.",
    "8": "Ukuran 18x4 dan 9x8; 9x8 kelilingnya lebih kecil.",
    "9": "Tidak ada; dua sisi terpendek sama dengan sisi terpanjang.",
    "10": "18x2, 16x4, dan 14x6 meter.",
}


def seed_database():
    with app.app_context():
        db.create_all()
        classroom = Classes(name="Load Test", school="Temporary", token="LOAD-TEST-ONLY", kkm=75)
        db.session.add(classroom)
        db.session.flush()

        students = []
        for index in range(1, STUDENTS + 1):
            student = User(
                username=f"loadtest{index:02d}",
                full_name=f"Load Test Student {index:02d}",
                level=0,
                gender="L",
                class_id=classroom.id,
                klasifikasi=1,
            )
            student.set_password(PASSWORD)
            students.append(student)
            db.session.add(student)
        db.session.flush()

        db.session.commit()
        return [(student.id, student.username) for student in students]


def csrf_token_from(html, pattern):
    match = re.search(pattern, html)
    if not match:
        raise RuntimeError("CSRF token tidak ditemukan di halaman")
    return match.group(1)


def run_student_flow(base_url, student):
    user_id, username = student
    started = time.perf_counter()
    with requests.Session() as client:
        login_page = client.get(f"{base_url}/login", timeout=30)
        login_csrf = csrf_token_from(
            login_page.text,
            r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"',
        )
        login = client.post(
            f"{base_url}/login",
            data={"username": username, "password": PASSWORD, "csrf_token": login_csrf},
            allow_redirects=False,
            timeout=30,
        )
        if login.status_code != 302:
            raise RuntimeError(f"login gagal untuk {username}: HTTP {login.status_code}")

        evaluation_page = client.get(
            f"{base_url}/evaluation/start/{user_id}/1",
            timeout=30,
        )
        if evaluation_page.status_code != 200:
            raise RuntimeError(f"halaman evaluasi gagal untuk {username}: HTTP {evaluation_page.status_code}")
        eval_csrf = csrf_token_from(
            evaluation_page.text,
            r'<meta name="csrf-token" content="([^"]+)"',
        )
        submit = client.post(
            f"{base_url}/evaluation/submit/{user_id}",
            json={"answers": ANSWERS, "time_taken": 90},
            headers={"X-CSRFToken": eval_csrf},
            timeout=30,
        )
        result = submit.json()
        if submit.status_code != 200 or result.get("status") != "success":
            raise RuntimeError(
                f"submit gagal untuk {username}: HTTP {submit.status_code}, {result.get('error', 'respons tidak valid')}"
            )

        return time.perf_counter() - started


def run_pretest_flow(base_url, student):
    user_id, username = student
    started = time.perf_counter()
    with requests.Session() as client:
        login_page = client.get(f"{base_url}/login", timeout=30)
        login_csrf = csrf_token_from(
            login_page.text,
            r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"',
        )
        login = client.post(
            f"{base_url}/login",
            data={"username": username, "password": PASSWORD, "csrf_token": login_csrf},
            allow_redirects=False,
            timeout=30,
        )
        if login.status_code != 302:
            raise RuntimeError(f"login gagal untuk {username}: HTTP {login.status_code}")

        pretest_page = client.get(f"{base_url}/pretest/start/{user_id}", timeout=30)
        if pretest_page.status_code != 200:
            raise RuntimeError(f"halaman pretest gagal untuk {username}: HTTP {pretest_page.status_code}")
        pretest_csrf = csrf_token_from(
            pretest_page.text,
            r'<meta name="csrf-token" content="([^"]+)"',
        )
        submit = client.post(
            f"{base_url}/pretest/submit/{user_id}",
            json={"answers": ANSWERS, "time_taken": 90},
            headers={"X-CSRFToken": pretest_csrf},
            timeout=30,
        )
        result = submit.json()
        if submit.status_code != 200 or result.get("status") != "success":
            raise RuntimeError(
                f"submit pretest gagal untuk {username}: HTTP {submit.status_code}, {result.get('error', 'respons tidak valid')}"
            )

        retry = client.post(
            f"{base_url}/pretest/submit/{user_id}",
            json={"answers": ANSWERS, "time_taken": 90},
            headers={"X-CSRFToken": pretest_csrf},
            timeout=30,
        )
        retry_result = retry.json()
        if retry.status_code != 200 or retry_result.get("status") != "success":
            raise RuntimeError(f"retry pretest tidak idempoten untuk {username}: HTTP {retry.status_code}")
        return time.perf_counter() - started


def run_concurrent_phase(students, worker, base_url):
    timings = []
    failures = []
    with ThreadPoolExecutor(max_workers=STUDENTS) as executor:
        futures = {executor.submit(worker, base_url, student): student for student in students}
        for future in as_completed(futures):
            try:
                timings.append(future.result())
            except Exception as error:
                failures.append(f"{futures[future][1]}: {error}")
    return timings, failures


def prepare_evaluation_phase(students):
    with app.app_context():
        classroom = Classes.query.filter_by(token="LOAD-TEST-ONLY").first()
        for user_id, _ in students:
            pretest = PretestResult.query.filter_by(user_id=user_id).first()
            pretest.ai_analysis = "{}"  # Simulate teacher analysis on the dummy record.
            db.session.add(Score(
                user_id=user_id,
                class_id=classroom.id,
                score_type="quiz",
                chapter="Bangun Datar",
                correct=10,
                incorrect=0,
                value=100,
            ))
            db.session.add(ActivityLog(user_id=user_id, activity_key="evaluation"))
        db.session.commit()


def main():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.config.update(TESTING=False)
    students = seed_database()
    server = make_server("127.0.0.1", 0, app, threaded=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    started = time.perf_counter()
    try:
        pretest_timings, pretest_failures = run_concurrent_phase(students, run_pretest_flow, base_url)
        with app.app_context():
            pretest_rows = PretestResult.query.all()
            pretest_saved = len(pretest_rows)
            pretest_distinct = db.session.query(PretestResult.user_id).distinct().count()
            answer_details_valid = all(
                len(json.loads(row.answer_details or "[]")) == len(ANSWERS)
                and all(
                    detail.get("jawaban_siswa") == ANSWERS.get(str(detail.get("nomor")))
                    for detail in json.loads(row.answer_details or "[]")
                )
                for row in pretest_rows
            )

        if pretest_failures or pretest_saved != STUDENTS or pretest_distinct != STUDENTS or not answer_details_valid:
            raise RuntimeError(
                f"Pretest phase failed: flows={len(pretest_timings)}, rows={pretest_saved}, students={pretest_distinct}, answers_valid={answer_details_valid}, errors={pretest_failures[:3]}"
            )

        prepare_evaluation_phase(students)
        evaluation_timings, evaluation_failures = run_concurrent_phase(students, run_student_flow, base_url)

        with app.app_context():
            evaluation_saved = EvaluationResult.query.count()
            evaluation_distinct = db.session.query(EvaluationResult.user_id).distinct().count()

        elapsed = time.perf_counter() - started
        print(f"Concurrent students: {STUDENTS}")
        print(f"Pretest: {len(pretest_timings)} successful, {len(pretest_failures)} failed, {pretest_saved} saved rows, answers verified, retries idempotent")
        print(f"Evaluation: {len(evaluation_timings)} successful, {len(evaluation_failures)} failed, {evaluation_saved} saved rows")
        print(f"Total duration: {elapsed:.2f}s")
        if pretest_timings:
            print(f"Pretest flow latency p50/max: {statistics.median(pretest_timings):.2f}s / {max(pretest_timings):.2f}s")
        if evaluation_timings:
            print(f"Evaluation flow latency p50/max: {statistics.median(evaluation_timings):.2f}s / {max(evaluation_timings):.2f}s")
        failures = pretest_failures + evaluation_failures
        for failure in failures[:10]:
            print(f"ERROR: {failure}")

        if failures or evaluation_saved != STUDENTS or evaluation_distinct != STUDENTS:
            raise SystemExit(1)
        print("RESULT: PASS — all 60 dummy students submitted both pretest and evaluation exactly once.")
    finally:
        server.shutdown()
        server_thread.join(timeout=5)
        TEMP_DIR.cleanup()


if __name__ == "__main__":
    main()

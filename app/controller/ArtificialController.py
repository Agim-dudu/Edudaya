import json
import os
import re
import requests
import logging
from app import db
from flask_login import current_user
from app.model import User, PretestResult, FinalResult, EvaluationResult
from flask import request, redirect, url_for, flash

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL          = "openrouter/auto"
BATCH_SIZE     = 15  # 2 batch untuk 30 siswa


def _build_prompt(chunk: list) -> str:
    return f"""Kamu adalah asisten pendidik ahli yang menganalisis hasil pretest numerasi siswa SD.
Gunakan bahasa Indonesia yang ramah dan mudah dipahami.

Data {len(chunk)} siswa:
{json.dumps(chunk, ensure_ascii=False, indent=2)}

Kembalikan HANYA array JSON murni (tanpa markdown, tanpa backticks) dengan {len(chunk)} objek:
[
  {{
    "user_id": <int>,
    "level_kemampuan": {{"level": "<Tinggi/Sedang/Rendah>", "deskripsi": "<1 kalimat>"}},
    "kelemahan":            [{{"topik": "", "keterangan": ""}}],
    "kekuatan":             [{{"topik": "", "keterangan": ""}}],
    "motivasi":             "<1-2 kalimat>",
    "rekomendasi_siswa":    [{{"topik": "", "saran": ""}}],
    "rekomendasi_guru":     [{{"topik": "", "saran": ""}}],
    "evaluasi_guru":        [{{"poin": ""}}]
  }}
]
Level: Tinggi>=80, Sedang=50-79, Rendah<50."""


def _call_openrouter(api_key: str, chunk: list) -> list:
    """
    Kirim satu chunk ke OpenRouter, kembalikan list hasil AI.
    Raise Exception jika gagal agar caller bisa handle per-batch.
    """
    prompt = _build_prompt(chunk)

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Batch Pretest Analytics"
        },
        json={
            "model":       MODEL,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  10000,  # cukup untuk 15 siswa + buffer aman
            "temperature": 0.3
        },
        timeout=120
    )
    resp.raise_for_status()
    resp_data = resp.json()

    if "error" in resp_data:
        err = resp_data["error"].get("message", str(resp_data["error"]))
        raise Exception(f"OpenRouter error: {err}")

    ai_text = resp_data["choices"][0]["message"]["content"].strip()

    # Strip markdown fence kalau ada
    ai_text = re.sub(r'^```(?:json)?\s*', '', ai_text)
    ai_text = re.sub(r'\s*```$',          '', ai_text).strip()

    logging.warning(f"RAW AI RESPONSE (chunk): {repr(ai_text[:500])}")

    ai_results = json.loads(ai_text)   # biarkan JSONDecodeError naik ke caller

    if len(ai_results) != len(chunk):
        raise Exception(
            f"Jumlah response tidak cocok: ekspektasi {len(chunk)}, "
            f"diterima {len(ai_results)}"
        )

    return ai_results


def batch_analyze_pretest_logic(teacher_id, class_id, user_ids=None):
    # ── Validasi hak akses ──────────────────────────────────────────────
    if teacher_id != current_user.id:
        flash("Akses ditolak: ID Guru tidak cocok.", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

    teacher_class_ids = [ct.class_id for ct in current_user.teacher_classes]
    if class_id not in teacher_class_ids:
        flash("Akses ditolak: Kelas bukan wewenang Anda.", "danger")
        return redirect(url_for('dashboard_result_pretest_analysis', user_id=teacher_id, class_id=class_id))

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        flash("Kunci API OpenRouter belum dikonfigurasi.", "danger")
        return redirect(url_for('dashboard_result_pretest_analysis', user_id=teacher_id, class_id=class_id))

    # ── Ambil data siswa ────────────────────────────────────────────────
    query = User.query.filter_by(class_id=class_id, level=0)
    if user_ids:
        query = query.filter(User.id.in_(user_ids))
    all_students = query.all()

    if not all_students:
        flash("Tidak ada siswa di kelas ini.", "warning")
        return redirect(url_for('dashboard_result_pretest_analysis', user_id=teacher_id, class_id=class_id))

    all_student_ids = [s.id for s in all_students]
    all_results = PretestResult.query.filter(
        PretestResult.user_id.in_(all_student_ids)
    ).all()

    submitted_ids = {r.user_id for r in all_results}
    unsubmitted   = [s.full_name for s in all_students if s.id not in submitted_ids]
    need_analysis = [r for r in all_results if r.ai_analysis is None]
    already_done  = [r for r in all_results if r.ai_analysis is not None]

    # ── Semua sudah dianalisis sebelumnya ───────────────────────────────
    if not need_analysis:
        flash(f"Semua {len(already_done)} siswa sudah dianalisis.", "info")
        return redirect(url_for('dashboard_result_pretest_analysis', user_id=teacher_id, class_id=class_id))

    # ── Peringatan siswa belum ujian (non-blocking) ─────────────────────
    if unsubmitted:
        flash(
            f"{len(unsubmitted)} siswa belum ujian: {', '.join(unsubmitted)}. Dilewati.",
            "warning"
        )

    # ── Susun payload lengkap ───────────────────────────────────────────
    student_lookup = {s.id: s for s in all_students}
    result_lookup  = {r.user_id: r for r in need_analysis}

    full_payload = []
    for r in need_analysis:
        s = student_lookup.get(r.user_id)
        full_payload.append({
            "user_id":        r.user_id,
            "nama":           s.full_name if s else f"Siswa {r.user_id}",
            "skor":           r.score,
            "benar":          r.correct,
            "total":          r.total,
            "waktu_menit":    (r.time_taken // 60) if r.time_taken else 0,
            "topic_scores":   json.loads(r.topic_scores)   if r.topic_scores   else {},
            "answer_details": json.loads(r.answer_details) if r.answer_details else []
        })

    # ── Proses per chunk ────────────────────────────────────────────────
    LEVEL_MAP     = {"Rendah": 0, "Sedang": 1, "Tinggi": 2}
    updated_count = 0
    failed_batches = []

    for batch_num, i in enumerate(range(0, len(full_payload), BATCH_SIZE), start=1):
        chunk = full_payload[i:i + BATCH_SIZE]
        logging.info(f"Memproses batch {batch_num}: siswa {i+1}–{i+len(chunk)}")

        try:
            ai_results = _call_openrouter(api_key, chunk)

        except json.JSONDecodeError as e:
            failed_batches.append(f"Batch {batch_num}: gagal parse JSON ({e})")
            continue
        except requests.exceptions.Timeout:
            failed_batches.append(f"Batch {batch_num}: timeout")
            continue
        except requests.exceptions.RequestException as e:
            failed_batches.append(f"Batch {batch_num}: koneksi gagal ({e})")
            continue
        except Exception as e:
            failed_batches.append(f"Batch {batch_num}: {e}")
            continue

        # ── Simpan hasil batch ke DB ────────────────────────────────────
        try:
            for item in ai_results:
                uid    = item.get("user_id")
                record = result_lookup.get(uid)
                if not record:
                    logging.warning(f"user_id {uid} tidak ditemukan di result_lookup, dilewati.")
                    continue

                record.ai_analysis = json.dumps(item, ensure_ascii=False)
                updated_count += 1

                user_record = student_lookup.get(uid)
                if user_record:
                    level_str = item.get("level_kemampuan", {}).get("level", "")
                    user_record.klasifikasi = LEVEL_MAP.get(level_str)  # 0 / 1 / 2 / None

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            failed_batches.append(f"Batch {batch_num}: gagal simpan DB ({e})")
            continue

    # ── Flash ringkasan hasil ───────────────────────────────────────────
    if updated_count:
        flash(f"Analisis {updated_count} siswa telah dilakukan.", "success")

    if already_done:
        flash(f"{len(already_done)} siswa lainnya sudah dianalisis sebelumnya.", "info")

    if failed_batches:
        flash(
            f"{len(failed_batches)} batch gagal diproses: {' | '.join(failed_batches)}",
            "danger"
        )

    if updated_count == 0 and not failed_batches:
        flash("Tidak ada data baru yang dianalisis.", "warning")

    return redirect(url_for('dashboard_result_pretest_analysis', user_id=teacher_id, class_id=class_id))



def _build_final_prompt(chunk: list) -> str:
    return f"""Kamu adalah asisten pendidik ahli yang menganalisis perkembangan belajar siswa SD.
Gunakan bahasa Indonesia yang ramah dan mudah dipahami.

Berikut data {len(chunk)} siswa yang berisi hasil PRETEST dan EVALUASI AKHIR mereka pada topik numerasi yang sama:
{json.dumps(chunk, ensure_ascii=False, indent=2)}

Bandingkan hasil pretest dan evaluasi akhir setiap siswa, lalu kembalikan HANYA array JSON murni (tanpa markdown, tanpa backticks) dengan {len(chunk)} objek:
[
  {{
    "user_id": <int>,
    "peningkatan_skor": <float>,
    "level_akhir": {{"level": "<Tinggi/Sedang/Rendah>", "deskripsi": "<1 kalimat>"}},
    "perkembangan": "<Meningkat/Stabil/Menurun>",
    "analisis_perkembangan": "<2-3 kalimat perbandingan pretest vs evaluasi>",
    "topik_meningkat":  [{{"topik": "", "keterangan": ""}}],
    "topik_menurun":    [{{"topik": "", "keterangan": ""}}],
    "motivasi":         "<1-2 kalimat motivasi untuk siswa>",
    "rekomendasi_siswa": [{{"topik": "", "saran": ""}}],
    "rekomendasi_guru":  [{{"topik": "", "saran": ""}}],
    "evaluasi_guru":     [{{"poin": ""}}]
  }}
]
Level: Tinggi>=80, Sedang=50-79, Rendah<50.
Perkembangan: Meningkat jika skor naik >5, Stabil jika selisih -5 s/d 5, Menurun jika turun >5."""


def _call_openrouter_final(api_key: str, chunk: list) -> list:
    prompt = _build_final_prompt(chunk)

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Batch Final Analytics"
        },
        json={
            "model":       MODEL,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  10000,
            "temperature": 0.3
        },
        timeout=120
    )
    resp.raise_for_status()
    resp_data = resp.json()

    if "error" in resp_data:
        err = resp_data["error"].get("message", str(resp_data["error"]))
        raise Exception(f"OpenRouter error: {err}")

    ai_text = resp_data["choices"][0]["message"]["content"].strip()
    ai_text = re.sub(r'^```(?:json)?\s*', '', ai_text)
    ai_text = re.sub(r'\s*```$',          '', ai_text).strip()

    logging.warning(f"RAW AI FINAL RESPONSE (chunk): {repr(ai_text[:500])}")

    ai_results = json.loads(ai_text)

    if len(ai_results) != len(chunk):
        raise Exception(
            f"Jumlah response tidak cocok: ekspektasi {len(chunk)}, "
            f"diterima {len(ai_results)}"
        )

    return ai_results


def batch_analyze_final_logic(teacher_id, class_id, user_ids=None):
    from app.model import FinalResult, EvaluationResult

    # ── Validasi hak akses ──────────────────────────────────────────────
    if teacher_id != current_user.id:
        flash("Akses ditolak: ID Guru tidak cocok.", "danger")
        return redirect(url_for('dashboard_result_final_analysis', user_id=teacher_id, class_id=class_id))

    teacher_class_ids = [ct.class_id for ct in current_user.teacher_classes]
    if class_id not in teacher_class_ids:
        flash("Akses ditolak: Kelas bukan wewenang Anda.", "danger")
        return redirect(url_for('dashboard_result_final_analysis', user_id=teacher_id, class_id=class_id))

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        flash("Kunci API OpenRouter belum dikonfigurasi.", "danger")
        return redirect(url_for('dashboard_result_final_analysis', user_id=teacher_id, class_id=class_id))

    # ── Ambil data siswa ────────────────────────────────────────────────
    query = User.query.filter_by(class_id=class_id, level=0)
    if user_ids:
        query = query.filter(User.id.in_(user_ids))
    all_students = query.all()

    if not all_students:
        flash("Tidak ada siswa di kelas ini.", "warning")
        return redirect(url_for('dashboard_result_final_analysis', user_id=teacher_id, class_id=class_id))

    all_student_ids = [s.id for s in all_students]

    # ── Ambil hasil pretest & evaluasi ─────────────────────────────────
    pretest_results = PretestResult.query.filter(
        PretestResult.user_id.in_(all_student_ids)
    ).all()

    evaluation_results = EvaluationResult.query.filter(
        EvaluationResult.user_id.in_(all_student_ids)
    ).all()

    pretest_lookup    = {r.user_id: r for r in pretest_results}
    evaluation_lookup = {r.user_id: r for r in evaluation_results}

    # ── Cek siswa yang sudah punya FinalResult ──────────────────────────
    existing_final = FinalResult.query.filter(
        FinalResult.user_id.in_(all_student_ids)
    ).all()
    already_done_ids = {f.user_id for f in existing_final}

    # ── Filter siswa yang siap dianalisis ──────────────────────────────
    # Syarat: punya pretest + evaluasi + belum ada final analysis
    no_pretest    = []
    no_evaluation = []
    ready_students = []

    for s in all_students:
        if s.id in already_done_ids:
            continue  # skip, sudah dianalisis
        has_pretest = s.id in pretest_lookup
        has_eval    = s.id in evaluation_lookup
        if not has_pretest:
            no_pretest.append(s.full_name)
        elif not has_eval:
            no_evaluation.append(s.full_name)
        else:
            ready_students.append(s)

    if no_pretest:
        flash(f"{len(no_pretest)} siswa belum mengerjakan pretest: {', '.join(no_pretest)}. Dilewati.", "warning")
    if no_evaluation:
        flash(f"{len(no_evaluation)} siswa belum mengerjakan evaluasi akhir: {', '.join(no_evaluation)}. Dilewati.", "warning")

    if not ready_students:
        if already_done_ids:
            flash(f"Semua {len(already_done_ids)} siswa sudah dianalisis.", "info")
        else:
            flash("Tidak ada siswa yang memenuhi syarat untuk dianalisis.", "warning")
        return redirect(url_for('dashboard_result_final_analysis', user_id=teacher_id, class_id=class_id))

    if already_done_ids:
        flash(f"{len(already_done_ids)} siswa sudah dianalisis sebelumnya, dilewati.", "info")

    # ── Susun payload ───────────────────────────────────────────────────
    student_lookup = {s.id: s for s in all_students}

    full_payload = []
    for s in ready_students:
        pre  = pretest_lookup[s.id]
        ev   = evaluation_lookup[s.id]
        full_payload.append({
            "user_id": s.id,
            "nama":    s.full_name,
            "pretest": {
                "skor":           pre.score,
                "benar":          pre.correct,
                "total":          pre.total,
                "waktu_menit":    (pre.time_taken // 60) if pre.time_taken else 0,
                "topic_scores":   json.loads(pre.topic_scores)   if pre.topic_scores   else {},
                "answer_details": json.loads(pre.answer_details) if pre.answer_details else []
            },
            "evaluasi_akhir": {
                "waktu_menit":    (ev.time_taken // 60) if ev.time_taken else 0,
                "topic_scores":   json.loads(ev.topic_scores)   if ev.topic_scores   else {},
                "answer_details": json.loads(ev.answer_details) if ev.answer_details else []
            }
        })

    # ── Proses per chunk ────────────────────────────────────────────────
    LEVEL_MAP      = {"Rendah": 0, "Sedang": 1, "Tinggi": 2}
    updated_count  = 0
    failed_batches = []

    for batch_num, i in enumerate(range(0, len(full_payload), BATCH_SIZE), start=1):
        chunk = full_payload[i:i + BATCH_SIZE]
        logging.info(f"Memproses final batch {batch_num}: siswa {i+1}–{i+len(chunk)}")

        try:
            ai_results = _call_openrouter_final(api_key, chunk)

        except json.JSONDecodeError as e:
            failed_batches.append(f"Batch {batch_num}: gagal parse JSON ({e})")
            continue
        except requests.exceptions.Timeout:
            failed_batches.append(f"Batch {batch_num}: timeout")
            continue
        except requests.exceptions.RequestException as e:
            failed_batches.append(f"Batch {batch_num}: koneksi gagal ({e})")
            continue
        except Exception as e:
            failed_batches.append(f"Batch {batch_num}: {e}")
            continue

        # ── Simpan ke DB ────────────────────────────────────────────────
        try:
            for item in ai_results:
                uid = item.get("user_id")
                if not uid or uid not in {s.id for s in ready_students}:
                    logging.warning(f"user_id {uid} tidak valid, dilewati.")
                    continue

                final_record = FinalResult(
                    user_id=uid,
                    ai_analysis=json.dumps(item, ensure_ascii=False)
                )
                db.session.add(final_record)
                updated_count += 1

                # Update klasifikasi user berdasarkan level akhir
                user_record = student_lookup.get(uid)
                if user_record:
                    level_str = item.get("level_akhir", {}).get("level", "")
                    user_record.klasifikasi = LEVEL_MAP.get(level_str)

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            failed_batches.append(f"Batch {batch_num}: gagal simpan DB ({e})")
            continue

    # ── Flash ringkasan ─────────────────────────────────────────────────
    if updated_count:
        flash(f"Analisis final {updated_count} siswa berhasil dilakukan.", "success")

    if failed_batches:
        flash(
            f"{len(failed_batches)} batch gagal: {' | '.join(failed_batches)}",
            "danger"
        )

    if updated_count == 0 and not failed_batches:
        flash("Tidak ada data baru yang dianalisis.", "warning")

    return redirect(url_for('dashboard_result_final_analysis', user_id=teacher_id, class_id=class_id))
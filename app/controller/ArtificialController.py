import json
import os
import re
import requests
from app import db
from flask_login import current_user
from app.model import User, PretestResult
from flask import request, redirect, url_for, flash

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/auto"

def batch_analyze_pretest_logic(teacher_id, class_id, user_ids=None):
    # ── Validasi hak akses ──────────────────────────────────────────────
    if teacher_id != current_user.id:
        flash("Akses ditolak: ID Guru tidak cocok.", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

    teacher_class_ids = [ct.class_id for ct in current_user.teacher_classes]
    if class_id not in teacher_class_ids:
        flash("Akses ditolak: Kelas bukan wewenang Anda.", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        flash("Kunci API OpenRouter belum dikonfigurasi.", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

    # ── Ambil data siswa ────────────────────────────────────────────────
    query = User.query.filter_by(class_id=class_id, level=0)
    if user_ids:
        query = query.filter(User.id.in_(user_ids))
    all_students = query.all()

    if not all_students:
        flash("Tidak ada siswa di kelas ini.", "warning")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

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
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

    # ── Peringatan siswa belum ujian (non-blocking) ─────────────────────
    if unsubmitted:
        flash(
            f"{len(unsubmitted)} siswa belum ujian: {', '.join(unsubmitted)}. Dilewati.",
            "warning"
        )

    # ── Susun payload untuk AI ──────────────────────────────────────────
    student_lookup = {s.id: s for s in all_students}
    payload = []
    for r in need_analysis:
        s = student_lookup.get(r.user_id)
        payload.append({
            "user_id":        r.user_id,
            "nama":           s.full_name if s else f"Siswa {r.user_id}",
            "skor":           r.score,
            "benar":          r.correct,
            "total":          r.total,
            "waktu_detik":    r.time_taken,
            "topic_scores":   json.loads(r.topic_scores)   if r.topic_scores   else {},
            "answer_details": json.loads(r.answer_details) if r.answer_details else []
        })

    prompt = f"""Kamu adalah asisten pendidik ahli yang menganalisis hasil pretest numerasi siswa SD.
Gunakan bahasa Indonesia yang ramah dan mudah dipahami.

Data {len(payload)} siswa:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Kembalikan HANYA array JSON murni (tanpa markdown, tanpa backticks) dengan {len(payload)} objek:
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

    # ── Panggil OpenRouter ──────────────────────────────────────────────
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Batch Pretest Analytics"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(750 * len(payload), 16000),
                "temperature": 0.3
            },
            timeout=120
        )
        resp.raise_for_status()
        resp_data = resp.json()

        if "error" in resp_data:
            err = resp_data["error"].get("message", str(resp_data["error"]))
            flash(f"OpenRouter error: {err}", "danger")
            return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

        ai_text = resp_data["choices"][0]["message"]["content"].strip()
        ai_text = re.sub(r'^```(?:json)?\s*', '', ai_text)
        ai_text = re.sub(r'\s*```$',          '', ai_text).strip()

        ai_results = json.loads(ai_text)

        if len(ai_results) != len(payload):
            flash(
                f"Response AI tidak lengkap: ekspektasi {len(payload)}, "
                f"diterima {len(ai_results)}.",
                "danger"
            )
            return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

        # ── Simpan ai_analysis per siswa ────────────────────────────────
        result_lookup = {r.user_id: r for r in need_analysis}
        updated_count = 0

        for item in ai_results:
            uid    = item.get("user_id")
            record = result_lookup.get(uid)
            if record:
                record.ai_analysis = json.dumps(item, ensure_ascii=False)
                updated_count += 1

        db.session.commit()

        # ── Flash sukses ────────────────────────────────────────────────
        # Contoh pesan: "Analisis 20 siswa telah dilakukan."
        flash(f"Analisis {updated_count} siswa telah dilakukan.", "success")

        # Jika ada sebagian yang sudah done sebelumnya, infokan juga
        if already_done:
            flash(
                f"{len(already_done)} siswa lainnya sudah dianalisis sebelumnya.",
                "info"
            )

        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))

    except json.JSONDecodeError as e:
        flash(f"Gagal parse response AI: {e}", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))
    except requests.exceptions.Timeout:
        flash("Request ke OpenRouter timeout.", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))
    except requests.exceptions.RequestException as e:
        flash(f"Gagal koneksi ke OpenRouter: {e}", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))
    except Exception as e:
        db.session.rollback()
        flash(f"Kesalahan internal: {e}", "danger")
        return redirect(url_for('dashboard_result_analysis', user_id=teacher_id, class_id=class_id))
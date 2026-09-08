import json
import os
from datetime import datetime
from app import db
from app.model import User, Score
from flask_login import current_user
from werkzeug.utils import secure_filename
from flask import abort, current_app, flash, request
from werkzeug.security import generate_password_hash

# Fungsi cek ekstensi bawaan Flask
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_student_profile(user_id):
    if user_id != current_user.id:
        abort(403)
        
    user = User.query.get_or_404(user_id)
    has_changes = False

    # =======================================================
    # 1. PROSES UPDATE FOTO PROFIL (MURNI FLASK - TANPA PILLOW)
    # =======================================================
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename != '':
            
            # Validasi ekstensi file pakai fungsi allowed_file di atas
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[-1].lower()

                # Tentukan folder resources luar (sejajar folder app)
                project_root = os.path.dirname(current_app.root_path)
                upload_folder = os.path.join(project_root, 'resources', 'images', 'avatars')
                os.makedirs(upload_folder, exist_ok=True)

                # Kunci nama berkas (Contoh: student_3.jpg)
                save_filename = f"student_{user.id}.{ext}"

                # --- LOGIKA REPLACE LINTAS EKSTENSI ---
                # Bersihkan file lama ber-ID sama yang ekvensinya berbeda (.png/.gif dll)
                for allowed_ext in {'png', 'jpg', 'jpeg', 'gif'}:
                    old_file_path = os.path.join(upload_folder, f"student_{user.id}.{allowed_ext}")
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except Exception:
                            pass

                # Langsung simpan file mentah pakai fungsi bawaan Flask
                file_path = os.path.join(upload_folder, save_filename)
                file.save(file_path)

                # Set kolom 'image' di database dengan nama filenya
                user.image = save_filename
                has_changes = True
            else:
                flash('Format file tidak didukung. Gunakan PNG, JPG, JPEG, atau GIF.', 'danger')
                return False

    # =======================================================
    # 2. PROSES UPDATE PASSWORD
    # =======================================================
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')

    if password or password_confirm:
        if password != password_confirm:
            flash("Konfirmasi password baru tidak cocok!", "danger")
            return False
        
        if len(password) < 6:
            flash("Password baru minimal harus 6 karakter!", "danger")
            return False

        user.set_password(password)
        has_changes = True

    # =======================================================
    # 3. DATABASE COMMIT
    # =======================================================
    if has_changes:
        try:
            db.session.commit()
            flash("Profil Anda (Foto/Password) berhasil diperbarui!", "success")
            return True
        except Exception as e:
            db.session.rollback()
            flash("Terjadi kesalahan sistem saat menyimpan perubahan.", "danger")
            return False
    else:
        flash("Tidak ada perubahan data yang disimpan.", "info")
        return True

def get_user_by_id(user_id):
    if user_id != current_user.id:
        abort(403)
    
    user = User.query.get(user_id)
    return user

def get_student_dashboard_stats(user_id):
    """Statistik & detail nilai halaman 'Nilai Saya' — murni dari hasil kuis (tabel Score)."""
    scores = Score.query.filter_by(user_id=user_id).all()

    chapters_meta = {
        "Bangun Datar": {"title": "Bangun Datar", "icon": "🔷"},
        "Bab 1": {"title": "Penjumlahan", "icon": "➕"},
        "Bab 2": {"title": "Pengurangan", "icon": "➖"},
    }

    bab_list = []
    for ch_key, meta in chapters_meta.items():
        ch_scores = [s for s in scores if s.chapter == ch_key]
        if not ch_scores:
            # Hanya tampilkan section yang benar-benar punya nilai
            continue

        completed = [s for s in ch_scores if s.value > 0]
        materials = []
        for s in ch_scores:
            materials.append({
                "icon": "🧩" if s.score_type == "quiz" else "📝",
                "title": f"{'Kuis' if s.score_type == 'quiz' else 'Latihan'} {meta['title']}",
                "updated_at": s.created_at or datetime.utcnow(),
                "completed": s.value > 0,
                "score": s.value,
            })

        progress = round((len(completed) / len(ch_scores)) * 100) if ch_scores else 0
        bab_list.append({
            "bab_title": meta["title"],
            "icon": meta["icon"],
            "completed": len(completed),
            "total": len(ch_scores),
            "bab_progress": progress,
            "materials": materials,
        })

    completed_chapters = len({s.chapter for s in scores if s.chapter})
    soal_dijawab = sum(s.correct + s.incorrect for s in scores)
    avg_score = round(sum(s.value for s in scores) / len(scores)) if scores else None

    return {
        "avg_score": avg_score,          # None -> template menampilkan '–'
        "completed_bab": completed_chapters,
        "soal_dijawab": soal_dijawab,
        "bab_list": bab_list,
    }

def get_student_overview_stats(user_id):
    """Statistik real untuk card ringkasan di dashboard siswa."""
    user = User.query.get(user_id)
    scores = Score.query.filter_by(user_id=user_id).all()

    # 📚 Materi selesai = jumlah bab/chapter berbeda yang sudah punya skor kuis
    materi_selesai = len({s.chapter for s in scores if s.chapter})

    # 🧩 Latihan dikerjakan = total soal yang sudah dijawab (benar + salah)
    latihan_dikerjakan = sum(s.correct + s.incorrect for s in scores)

    # ⭐ Nilai rata-rata & terbaik = MURNI dari nilai kuis (pretest tidak dihitung)
    def _avg(s_list):
        return round(sum(s.value for s in s_list) / len(s_list)) if s_list else None

    nilai_rata = _avg(scores)
    nilai_terbaik = max((s.value for s in scores), default=None)

    # 🏅 Peringkat kelas & leaderboard = ranking siswa sekelas (rata-rata nilai, lalu star)
    peringkat = None
    total_kelas = 0
    leaderboard = []
    classmates = []
    if user.class_id:
        classmates = User.query.filter_by(level=0, class_id=user.class_id).all()
        total_kelas = len(classmates)

        def _rank_key(m):
            avg = _avg(m.scores)
            return (avg if avg is not None else -1, m.star or 0)

        ranked = sorted(classmates, key=_rank_key, reverse=True)
        peringkat = ranked.index(user) + 1

        for m in ranked[:3]:
            avg = _avg(m.scores)  # murni nilai kuis
            leaderboard.append({
                "full_name": m.full_name,
                "is_me": m.id == user.id,
                "score": avg,  # None -> template tampil '–'
            })

    # 📋 Detail nilai per materi (dari tabel Score, terbaru dulu)
    icons = {"Bangun Datar": "🔷", "Bab 1": "➕", "Bab 2": "➖"}
    titles = {"Bangun Datar": "Kuis Bangun Datar", "Bab 1": "Kuis Penjumlahan", "Bab 2": "Kuis Pengurangan"}
    nilai_detail = []
    for s in sorted(scores, key=lambda x: x.created_at or datetime.utcnow(), reverse=True):
        nilai_detail.append({
            "icon": icons.get(s.chapter, "📝"),
            "title": titles.get(s.chapter, f"Kuis {s.chapter}"),
            "created_at": s.created_at,
            "value": s.value,
            "label": "Sangat Baik" if s.value >= 85 else "Baik" if s.value >= 75 else "Perlu Latihan",
        })

    return {
        "materi_selesai": materi_selesai,
        "latihan_dikerjakan": latihan_dikerjakan,
        "kuis_selesai": len(scores),
        "nilai_rata": nilai_rata,
        "nilai_terbaik": nilai_terbaik,
        "peringkat": peringkat,
        "total_kelas": total_kelas,
        "leaderboard": leaderboard,
        "nilai_detail": nilai_detail,
    }

def show_student_ai_analysis(user_id):
    if user_id != current_user.id:
        abort(403)

    if current_user.level != 0:
        abort(403)

    pretest = current_user.pretest_result
    
    # Ambil data ai_analysis jika pretest dan ai_analysis itu ada
    ai_analysis_data = None
    if pretest and pretest.ai_analysis:
        try:
            ai_analysis_data = json.loads(pretest.ai_analysis)
        except (json.JSONDecodeError, TypeError):
            # Payload bukan JSON valid — tampilkan halaman tanpa analisis, bukan error 500
            ai_analysis_data = None

    # Selalu kembalikan struktur dictionary yang sama agar route tidak error
    return {
        'student': current_user,
        'ai_analysis': ai_analysis_data
    }
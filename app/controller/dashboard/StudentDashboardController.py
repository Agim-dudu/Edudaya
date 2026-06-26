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
    scores = Score.query.filter_by(user_id=user_id).all()

    chapters = [
        {"key": "Bab 1", "title": "Operasi Hitung Dasar", "icon": "🛶"},
        {"key": "Bab 2", "title": "Geometri & Pola", "icon": "🔷"},
    ]

    bab_list = []
    total_value = 0
    total_completed = 0
    total_submateri = 0

    for ch in chapters:
        ch_scores = [s for s in scores if s.chapter == ch["key"]]
        completed = [s for s in ch_scores if s.value > 0]
        total = max(len(ch_scores), 4)

        materials = []
        for i, s in enumerate(ch_scores):
            materials.append({
                "icon": "📝" if s.score_type == "quiz" else "📄",
                "title": f"{'Kuis' if s.score_type == 'quiz' else 'Latihan'} {ch['key']}",
                "updated_at": s.created_at or datetime.utcnow(),
                "completed": s.value > 0,
                "score": s.value,
            })

        progress = round((len(completed) / total) * 100) if total > 0 else 0
        bab_list.append({
            "bab_title": ch["title"],
            "icon": ch["icon"],
            "completed": len(completed),
            "total": total,
            "bab_progress": progress,
            "materials": materials,
        })
        total_submateri += len(ch_scores)

    completed_count = sum(b["completed"] for b in bab_list)
    total_count = sum(b["total"] for b in bab_list)
    avg_score = round(sum(s.value for s in scores if s.value > 0) / max(sum(1 for s in scores if s.value > 0), 1))

    return {
        "avg_score": avg_score,
        "completed_bab": completed_count,
        "total_bab": total_count,
        "total_submateri": total_submateri,
        "bab_list": bab_list,
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
        ai_analysis_data = json.loads(pretest.ai_analysis)

    # Selalu kembalikan struktur dictionary yang sama agar route tidak error
    return {
        'student': current_user,
        'ai_analysis': ai_analysis_data
    }
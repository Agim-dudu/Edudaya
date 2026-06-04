import json
import os
from app import db
from app.model import User
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
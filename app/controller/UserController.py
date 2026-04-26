from app.model import User, Token, Classes, UserClasses
from flask import request, redirect, url_for, flash, jsonify, session
from flask_login import current_user
from flask_login import login_user, logout_user
from app import response, app, db
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token, create_refresh_token

def login_siswa():
    try:
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username dan Password harus diisi.', 'danger')
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Username atau Password salah.', 'danger')
            return redirect(url_for('login'))

        # Tambahan: cek apakah role user adalah 0 (siswa)
        if user.level != 0:
            flash('Akun Anda bukan siswa.', 'danger')
            return redirect(url_for('login'))
        
        # Ini akan membuat Flask menggunakan durasi 1 hari yang diset tadi
        session.permanent = True

        # # Login Flask-Login
        login_user(user)
        
        nama_tampilan = user.full_name if user.full_name else user.username

        flash(f'Selamat Belajar {nama_tampilan} 🥳🥳🥳', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        print(e)
        flash('Terjadi kesalahan saat login.', 'danger')
        return redirect(url_for('login'))
    
def logout():
    user_id = str(current_user.id)
    logout_user()
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('index'))
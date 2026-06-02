from app.model import User, Classes
from app import app, db
from flask_login import login_user, logout_user
from flask import request, redirect, url_for, flash, session

def login_admin():
    try:
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username dan Password harus diisi.", "danger")
            return redirect(url_for("login_admin"))

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Username atau Password salah.", "danger")
            return redirect(url_for("login_admin"))

        # Cek apakah role user adalah 2 (admin)
        if user.level != 2:
            flash("Akun Anda bukan admin.", "danger")
            return redirect(url_for("login_admin"))

        session.permanent = True
        login_user(user)

        nama_tampilan = user.full_name if user.full_name else user.username
        flash(f"Selamat Datang {nama_tampilan} 👨🏻‍💻👨🏻‍💻👨🏻‍💻", "success")
        return redirect(url_for("index"))

    except Exception as e:
        print(f"Error Login Admin: {e}")
        flash("Terjadi kesalahan saat login admin.", "danger")
        return redirect(url_for("login_admin"))


def login_teacher():
    try:
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username dan Password harus diisi.", "danger")
            return redirect(url_for("login_teacher"))

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Username atau Password salah.", "danger")
            return redirect(url_for("login_teacher"))

        # Cek apakah level user adalah 1 (guru)
        if user.level != 1:
            flash("Akun Anda bukan guru.", "danger")
            return redirect(url_for("login_teacher"))

        session.permanent = True
        login_user(user)

        nama_tampilan = user.full_name if user.full_name else user.username
        flash(f"Selamat Datang {nama_tampilan} 👩🏻‍🏫👨🏻‍🏫", "success")
        return redirect(url_for("index"))

    except Exception as e:
        print(f"Error Login Teacher: {e}")
        flash("Terjadi kesalahan saat login guru.", "danger")
        return redirect(url_for("login_teacher"))


def login_siswa():
    try:
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username dan Password harus diisi.", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Username atau Password salah.", "danger")
            return redirect(url_for("login"))

        # Cek apakah role user adalah 0 (siswa)
        if user.level != 0:
            flash("Akun Anda bukan siswa.", "danger")
            return redirect(url_for("login"))

        session.permanent = True
        login_user(user)

        nama_tampilan = user.full_name if user.full_name else user.username
        flash(f"Selamat Belajar {nama_tampilan} 🥳🥳🥳", "success")
        return redirect(url_for("index"))

    except Exception as e:
        print(f"Error Login Siswa: {e}")
        flash("Terjadi kesalahan saat login siswa.", "danger")
        return redirect(url_for("login"))


def register():
    try:
        full_name = request.form.get("full_name")
        username = request.form.get("username")
        gender = request.form.get("gender")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        token = request.form.get("token")

        # Validasi input kosong
        if not (full_name and username and gender and password and confirm_password and token):
            flash("Semua field harus diisi.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Kata sandi dan konfirmasi tidak cocok.", "danger")
            return redirect(url_for("register"))

        # Cek username sudah ada
        if User.query.filter_by(username=username).first():
            flash("Username sudah digunakan.", "danger")
            return redirect(url_for("register"))

        # Cek validitas token kelas
        token_record = Classes.query.filter_by(token=token).first()
        if not token_record:
            flash("Token kelas tidak valid.", "danger")
            return redirect(url_for("register"))

        # 🔥 FIX LOGIK: Buat user baru (Siswa) langsung menempelkan class_id di sini
        user = User(
            full_name=full_name,
            username=username,
            gender=gender,
            level=0,                        # Kunci otomatis ke level Siswa
            class_id=token_record.id        # Hubungan langsung ke tabel Classes tanpa tabel jembatan
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit() # Cukup 1 kali commit sekarang! Lebih bersih dan aman.

        flash("Pendaftaran berhasil! Silakan login.", "success")
        return redirect(url_for("login"))

    except Exception as e:
        db.session.rollback()
        print(f"Error Register Siswa: {e}")
        flash("Terjadi kesalahan saat pendaftaran.", "danger")
        return redirect(url_for("register"))


def logout():
    logout_user()
    flash("Anda telah berhasil logout.", "success")
    return redirect(url_for("index"))
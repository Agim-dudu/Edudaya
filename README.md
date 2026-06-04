# 🚀 Veldora Framework

Veldora adalah framework berbasis Python yang dibangun di atas Flask
dengan pendekatan MVC (Model-View-Controller) untuk membangun aplikasi
web yang terstruktur, scalable, dan clean.

------------------------------------------------------------------------

## 📦 Requirements

-   Python 3.8+
-   pip

------------------------------------------------------------------------

## ⚙️ Installation Guide

### 🔹 0. Buat file konfigurasi lingkungan

Sebelum menjalankan aplikasi, salin file contoh konfigurasi:

```bash
cp .env.example .env
```

Lalu buka `.env` dan isi nilai database serta kunci rahasia sesuai lingkungan Anda.

------------------------------------------------------------------------

### 🔹 1. Membuat Virtual Environment (venv)

#### 🪟 Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### 🐧 Linux / 🍎 MacOS

```bash
python3 -m venv venv
source venv/bin/activate
```

------------------------------------------------------------------------

### 🔹 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

------------------------------------------------------------------------

### 🔹 3. Siapkan konfigurasi `.env`

Salin file contoh konfigurasi:

```bash
cp .env.example .env
```

Buka `.env` dan isi nilai database serta kunci rahasia:

- `DB_HOST`
- `DB_PORT`
- `DB_DATABASE`
- `DB_USERNAME`
- `DB_PASSWORD`
- `JWT_SECRET`
- `SECRET_KEY`

> Jika database belum ada, buat terlebih dahulu di MySQL/MariaDB:
>
> ```bash
> mysql -u root -p -e "CREATE DATABASE edudaya CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
> ```

------------------------------------------------------------------------

### 🔹 4. Inisialisasi Database dan Seed Data

Sebelum menjalankan migrasi, pastikan database sudah dibuat sesuai nilai pada file `.env`.

```bash
CREATE DATABASE edudaya;
```

Jika ini pertama kali Anda menjalankan migrasi pada project ini, inisialisasi folder migrasi:

```bash
export FLASK_APP=server.py
flask db init
```

Kemudian buat dan terapkan migrasi:

```bash
export FLASK_APP=server.py
flask db migrate -m "Initial migration"
flask db upgrade
```

Terakhir jalankan seeder

```bash
# Pastikan berada di root project dan menggunakan Python dari virtual environment
export PYTHONPATH=.

python seeders/class_seed.py
python seeders/user_seed.py
```



------------------------------------------------------------------------

### 🔹 5. Menjalankan Project

#### Windows (CMD)

```bash
set FLASK_APP=server.py
flask run
```

#### Windows (PowerShell)

```powershell
$env:FLASK_APP = "server.py"
flask run
```

#### Linux / MacOS

```bash
export FLASK_APP=server.py
export FLASK_ENV=development
flask run --host=127.0.0.1 --port=5000
```

Atau jalankan langsung:

```bash
python3 server.py
```

> Jika Anda menggunakan MySQL, pastikan server database berjalan dan nilai `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, dan `DB_PASSWORD` di `.env` sudah benar.

------------------------------------------------------------------------

## 🌐 Akses Aplikasi

http://127.0.0.1:5000/

------------------------------------------------------------------------

## 👨‍💻 Author

Agim Dudu (agimdudu)

------------------------------------------------------------------------

## 📄 License

MIT License

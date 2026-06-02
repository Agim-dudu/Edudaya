from app.model import User

def get_amount_student_by_teacher(user_id):
    # 1. Cari objek guru berdasarkan user_id
    teacher = User.query.get(user_id)
    if not teacher or teacher.level != 1: # Pastikan dia ada dan dia adalah Guru
        return 0

    # 2. Ambil semua list class_id yang diampu oleh guru tersebut dari tabel jembatan
    class_ids = [rel.class_id for rel in teacher.teacher_classes]

    if not class_ids:
        return 0

    # 3. 🔥 FIX: Hitung jumlah siswa unik (level=0) yang memiliki class_id di dalam daftar kelas guru tersebut
    amount_student = (
        User.query
        .filter(
            User.level == 0,
            User.class_id.in_(class_ids) # Cukup filter langsung di tabel User tanpa .join()
        )
        .count()
    )

    return amount_student


def get_amount_class_by_teacher(user_id):
    # 1. Cari objek guru berdasarkan user_id
    teacher = User.query.get(user_id)
    if not teacher or teacher.level != 1:
        return 0

    # 2. 🔥 FIX: Hitung jumlah kelas langsung dari relasi teacher_classes yang baru
    amount_class = len(teacher.teacher_classes)
    
    return amount_class
from app import db
from datetime import datetime

# =========================================================================
# MODEL ACTIVITY LOG (Mencatat Aktivitas Membaca/Mandiri yang Sudah Selesai)
# =========================================================================
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # 🔗 Hubungan ke Siswa yang melakukan aktivitas
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Kunci Unik Aktivitas (Contoh: 'sub_materi_1_aktivitas_1')
    activity_key = db.Column(db.String(100), nullable=False)
    
    # Waktu ketika siswa menyelesaikan aktivitas tersebut
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ActivityLog user_id={self.user_id} activity_key={self.activity_key}>'
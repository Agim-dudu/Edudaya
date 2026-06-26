import json
import os
import re
import requests
from app import db
from flask_login import current_user
from app.model import User, PretestResult, ActivityLog
from flask import request, redirect, url_for, flash, jsonify

def bab1_chapter1_activity(user_id):
    if user_id != current_user.id:
        return jsonify({"status": "error", "message": "Akses ditolak (403)."}), 403

    if current_user.level in (1, 2):
        return jsonify({"status": "forbidden", "message": "Guru/Admin tidak dapat menyelesaikan aktivitas siswa."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User tidak ditemukan."}), 404

    ACTIVITY_KEY = "bab1_chapter1_activity"
    NILAI_PROGRES_BARU = 0

    already_submitted = ActivityLog.query.filter_by(user_id=user_id, activity_key=ACTIVITY_KEY).first()
    if already_submitted:
        return jsonify({"status": "info", "message": "Aktivitas sudah pernah diselesaikan."}), 200

    log = ActivityLog(user_id=user_id, activity_key=ACTIVITY_KEY)
    db.session.add(log)

    if user.progress < NILAI_PROGRES_BARU:
        user.progress = NILAI_PROGRES_BARU

    db.session.commit()

    return jsonify({"status": "success", "message": "Aktivitas berhasil diselesaikan."}), 200


def bab1_chapter2_activity(user_id):
    if user_id != current_user.id:
        return jsonify({"status": "error", "message": "Akses ditolak (403)."}), 403

    if current_user.level in (1, 2):
        return jsonify({"status": "forbidden", "message": "Guru/Admin tidak dapat menyelesaikan aktivitas siswa."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User tidak ditemukan."}), 404

    ACTIVITY_KEY = "bab1_chapter2_activity"
    NILAI_PROGRES_BARU = 0

    already_submitted = ActivityLog.query.filter_by(user_id=user_id, activity_key=ACTIVITY_KEY).first()
    if already_submitted:
        return jsonify({"status": "info", "message": "Aktivitas sudah pernah diselesaikan."}), 200

    log = ActivityLog(user_id=user_id, activity_key=ACTIVITY_KEY)
    db.session.add(log)

    if user.progress < NILAI_PROGRES_BARU:
        user.progress = NILAI_PROGRES_BARU

    db.session.commit()

    return jsonify({"status": "success", "message": "Aktivitas berhasil diselesaikan."}), 200


def bab2_chapter1_activity(user_id):
    if user_id != current_user.id:
        return jsonify({"status": "error", "message": "Akses ditolak (403)."}), 403

    if current_user.level in (1, 2):
        return jsonify({"status": "forbidden", "message": "Guru/Admin tidak dapat menyelesaikan aktivitas siswa."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User tidak ditemukan."}), 404

    ACTIVITY_KEY = "bab2_chapter1_activity"
    NILAI_PROGRES_BARU = 0

    already_submitted = ActivityLog.query.filter_by(user_id=user_id, activity_key=ACTIVITY_KEY).first()
    if already_submitted:
        return jsonify({"status": "info", "message": "Aktivitas sudah pernah diselesaikan."}), 200

    log = ActivityLog(user_id=user_id, activity_key=ACTIVITY_KEY)
    db.session.add(log)

    if user.progress < NILAI_PROGRES_BARU:
        user.progress = NILAI_PROGRES_BARU

    db.session.commit()

    return jsonify({"status": "success", "message": "Aktivitas berhasil diselesaikan."}), 200


def bab2_chapter2_activity(user_id):
    if user_id != current_user.id:
        return jsonify({"status": "error", "message": "Akses ditolak (403)."}), 403

    if current_user.level in (1, 2):
        return jsonify({"status": "forbidden", "message": "Guru/Admin tidak dapat menyelesaikan aktivitas siswa."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User tidak ditemukan."}), 404

    ACTIVITY_KEY = "bab2_chapter2_activity"
    NILAI_PROGRES_BARU = 0

    already_submitted = ActivityLog.query.filter_by(user_id=user_id, activity_key=ACTIVITY_KEY).first()
    if already_submitted:
        return jsonify({"status": "info", "message": "Aktivitas sudah pernah diselesaikan."}), 200

    log = ActivityLog(user_id=user_id, activity_key=ACTIVITY_KEY)
    db.session.add(log)

    if user.progress < NILAI_PROGRES_BARU:
        user.progress = NILAI_PROGRES_BARU

    db.session.commit()

    return jsonify({"status": "success", "message": "Aktivitas berhasil diselesaikan."}), 200
    


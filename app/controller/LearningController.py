import json
from app import db
from sqlalchemy import func
from app.model import User, Classes, LearningProgress
from flask_login import current_user
from flask import jsonify, request

MATERIAL_CATALOG = [
    {
        'bab_key': 'medium_1',
        'bab_title': 'Bab 1 — Operasi Hitung Dasar',
        'icon': '🔢',
        'materials': [
            {'key': 'medium_1_1',   'title': 'Pengenalan Penjumlahan',     'icon': '🛶', 'url': '/learning/medium/1/1'},
            {'key': 'medium_1_2',   'title': 'Penjumlahan Lanjutan',       'icon': '🌾', 'url': '/learning/medium/1/2'},
            {'key': 'medium_1_3',   'title': 'Pengertian Pengurangan',     'icon': '🍃', 'url': '/learning/medium/1/3'},
            {'key': 'medium_1_4',   'title': 'Pengurangan Lanjutan',       'icon': '🎣', 'url': '/learning/medium/1/4'},
            {'key': 'medium_1_quiz','title': 'Kuis Bab 1',                 'icon': '🧩', 'url': '/learning/medium/1/quiz'},
        ],
    },
]


def save_learning_progress(user_id):
    if user_id != current_user.id:
        return jsonify({"error": "Akses ditolak"}), 403

    data = request.get_json()
    if not data or 'material_key' not in data:
        return jsonify({"error": "Data tidak lengkap"}), 400

    material_key = data['material_key']
    score = data.get('score', 0)
    completed = data.get('completed', False)

    progress = LearningProgress.query.filter_by(
        user_id=user_id,
        material_key=material_key
    ).first()

    if progress:
        if score > progress.score:
            progress.score = score
        if completed:
            progress.completed = True
    else:
        parts = material_key.rsplit('_', 1)
        lesson = parts[0] if len(parts) > 1 else material_key
        progress = LearningProgress(
            user_id=user_id,
            lesson_key=lesson,
            material_key=material_key,
            score=score,
            completed=completed
        )
        db.session.add(progress)

    user = User.query.get(user_id)
    if user and completed:
        if material_key.endswith('_quiz'):
            chapter_prefix = material_key.rsplit('_', 1)[0]
            chapter_materials = LearningProgress.query.filter(
                LearningProgress.user_id == user_id,
                LearningProgress.material_key.like(chapter_prefix + '_%'),
                LearningProgress.material_key != material_key
            ).all()
            for m in chapter_materials:
                if not m.completed:
                    m.completed = True

        total_completed = LearningProgress.query.filter_by(
            user_id=user_id, completed=True
        ).count()
        user.progress = total_completed

    db.session.commit()

    return jsonify({
        "status": "success",
        "score": progress.score,
        "completed": progress.completed
    })


def get_learning_progress(user_id):
    if user_id != current_user.id:
        return jsonify({"error": "Akses ditolak"}), 403

    material_key = request.args.get('material_key')
    if not material_key:
        return jsonify({"error": "material_key diperlukan"}), 400

    progress = LearningProgress.query.filter_by(
        user_id=user_id,
        material_key=material_key
    ).first()

    if progress:
        return jsonify({
            "found": True,
            "score": progress.score,
            "completed": progress.completed
        })
    else:
        return jsonify({
            "found": False,
            "score": 0,
            "completed": False
        })


def get_all_progress(user_id):
    if user_id != current_user.id:
        return jsonify({"error": "Akses ditolak"}), 403

    records = LearningProgress.query.filter_by(user_id=user_id).all()
    result = {
        r.material_key: {
            "score": r.score,
            "completed": r.completed
        }
        for r in records
    }
    return jsonify(result)


def get_student_dashboard_stats(user_id):
    user = User.query.get(user_id)
    if not user or user.level != 0:
        return {}

    progress_records = LearningProgress.query.filter_by(user_id=user_id).all()
    progress_map = {r.material_key: r for r in progress_records}

    total_bab = len(MATERIAL_CATALOG)
    completed_bab = 0
    for bab in MATERIAL_CATALOG:
        all_done = True
        for item in bab['materials']:
            p = progress_map.get(item['key'])
            if not p or not p.completed:
                all_done = False
                break
        if all_done:
            completed_bab += 1

    total_all = sum(len(bab['materials']) for bab in MATERIAL_CATALOG)
    total_submateri = sum(
        len([it for it in bab['materials'] if not it['key'].endswith('_quiz')])
        for bab in MATERIAL_CATALOG
    )
    total_score = sum(r.score for r in progress_records)
    avg_score = round(total_score / total_all) if total_all > 0 else 0

    next_material = None
    bab_list = []
    for bab in MATERIAL_CATALOG:
        bab_completed = 0
        bab_total = len(bab['materials'])
        items_detail = []
        for item in bab['materials']:
            p = progress_map.get(item['key'])
            if p and p.completed:
                bab_completed += 1
            items_detail.append({
                'key': item['key'],
                'title': item['title'],
                'icon': item['icon'],
                'url': item['url'] + '/' + str(user_id),
                'score': p.score if p else 0,
                'completed': p.completed if p else False,
                'updated_at': p.updated_at if p else None,
            })

            if next_material is None and (not p or not p.completed):
                next_material = {
                    'bab_title': bab['bab_title'],
                    'title': item['title'],
                    'icon': item['icon'],
                    'url': item['url'] + '/' + str(user_id),
                    'score': p.score if p else 0,
                    'completed': p.completed if p else False,
                    'bab_progress': round((bab_completed / bab_total) * 100),
                }

        bab_list.append({
            'bab_key': bab['bab_key'],
            'bab_title': bab['bab_title'],
            'icon': bab['icon'],
            'completed': bab_completed,
            'total': bab_total,
            'bab_progress': round((bab_completed / bab_total) * 100),
            'materials': items_detail,
        })

    class_id = user.class_id
    ranking = None
    leaderboard = []
    if class_id:
        classmates = User.query.filter(
            User.class_id == class_id,
            User.level == 0
        ).all()

        leaderboard_rows = []
        for c in classmates:
            records = LearningProgress.query.filter_by(user_id=c.id).all()
            c_completed = sum(1 for r in records if r.completed)
            c_total_score = sum(r.score for r in records)
            leaderboard_rows.append({
                'name': c.full_name,
                'completed': c_completed,
                'total_score': c_total_score,
                'is_me': c.id == user_id,
            })

        leaderboard_rows.sort(key=lambda x: (x['completed'], x['total_score']), reverse=True)
        for rank, row in enumerate(leaderboard_rows, 1):
            if row['is_me']:
                ranking = rank
            if rank <= 5:
                leaderboard.append({'rank': rank, **row})

    return {
        'total_bab': total_bab,
        'completed_bab': completed_bab,
        'total_submateri': total_submateri,
        'completed_count': completed_bab,
        'total_materi': total_bab,
        'avg_score': avg_score,
        'ranking': ranking,
        'leaderboard': leaderboard,
        'class_name': user.student_class_obj.name if user.student_class_obj else '',
        'class_school': user.student_class_obj.school if user.student_class_obj else '',
        'next_material': next_material,
        'bab_list': bab_list,
    }

# from app.model.user import User
# from flask import request
# import os
# from app import response, app, db
# import uuid
# from datetime import datetime, timedelta
# from flask_jwt_extended import create_access_token, create_refresh_token

# def CreateAdmin():
#     try:
#         username = request.form.get('username')
#         email = request.form.get('email')
#         password = request.form.get('password')
#         level = 1

#         users = User(username=username, email=email, level=level)
#         users.set_password(password)
#         db.session.add(users)
#         db.session.commit()

#         return response.success('', 'Sukses Menambahkan Data Admin!')
#     except Exception as e:
#         print(e)
#         return response.badRequest([], 'Terjadi kesalahan saat menambahkan data admin.')

# def singleObject(data):
#     return {
#         'id': data.id,
#         'username': data.username,
#         'email': data.email,
#         'level': data.level
#     }

# def login():
#     try:
#         email = request.form.get('email')
#         password = request.form.get('password')

#         user = User.query.filter_by(email=email).first()

#         if not user or not user.check_password(password):
#             return response.badRequest([], 'Email atau Password tidak ditemukan')

#         data = singleObject(user)

#         expires = timedelta(days=7)
#         expires_refresh = timedelta(days=7)

#         access_token = create_access_token(identity=data, fresh=True, expires_delta=expires)
#         refresh_token = create_refresh_token(identity=data, expires_delta=expires_refresh)

#         return response.success({
#             "data": data,
#             "access_token": access_token,
#             "refresh_token": refresh_token,
#         }, "Sukses Login!")
        
#     except Exception as e:
#         print(e)
#         return response.badRequest([], 'Terjadi kesalahan saat login.')

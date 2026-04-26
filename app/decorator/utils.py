from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, login_required

def level_required(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.level != role:
                flash('You do not have permission to access this page.', 'warning')
                return redirect(url_for('index'))  # Ganti 'index' dengan route yang sesuai
            return f(*args, **kwargs)
        return decorated_function
    return decorator

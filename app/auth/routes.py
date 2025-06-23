from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required
from app.models.user import User
from app import db

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        user_type = data.get('user_type', 'customer')

        # 验证输入
        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'error': '用户名已存在'}), 400
            flash('用户名已存在')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'error': '邮箱已注册'}), 400
            flash('邮箱已注册')
            return redirect(url_for('auth.register'))

        # 创建新用户
        user = User(username=username, email=email, user_type=user_type)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        if request.is_json:
            return jsonify({'message': '注册成功', 'user_id': user.id}), 201

        flash('注册成功')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_type'] = user.user_type
            if request.is_json:
                return jsonify({
                    'message': '登录成功',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'user_type': user.user_type
                    }
                }), 200
            return redirect(url_for('main.index'))

        if request.is_json:
            return jsonify({'error': '用户名或密码错误'}), 401

        flash('用户名或密码错误')
        return redirect(url_for('auth.login'))

    return render_template('login.html')

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        # 在此处添加处理逻辑：查找用户、发送邮件等
        flash('如果该邮箱已注册，我们会向您发送重置链接。')
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录。')
    return redirect(url_for('main.index'))
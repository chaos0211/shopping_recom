from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import current_user, login_required
from app.models.user import User
from app.models.product import Product, Category
from app.models.order import Order, OrderItem
from app.models.review import Review, Favorite, BrowsingHistory
from app import db
from datetime import datetime
import json

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    # 获取热门商品
    popular_products = Product.query.limit(8).all()
    categories = Category.query.all()

    return render_template('index.html',
                           products=popular_products,
                           categories=categories)


@bp.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')

    query = Product.query
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search:
        query = query.filter(Product.name.contains(search))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    categories = Category.query.all()

    return render_template('products.html',
                           products=pagination,
                           categories=categories)


@bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).all()

    # 判断是否收藏
    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first() is not None

    # 记录浏览历史
    if current_user.is_authenticated:
        history = BrowsingHistory.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if history:
            history.view_count += 1
            history.timestamp = datetime.utcnow()
        else:
            history = BrowsingHistory(
                user_id=current_user.id,
                product_id=product_id
            )
            db.session.add(history)
        db.session.commit()

    return render_template('product_detail.html',
                           product=product,
                           reviews=reviews,
                           is_favorited=is_favorited)

@bp.route('/api/products/<int:product_id>/related')
def related_products(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()

    data = [{
        'id': p.id,
        'name': p.name,
        'price': float(p.price),
        'image_url': p.image_url,
        'average_rating': p.average_rating
    } for p in related]

    return jsonify(data)


@bp.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    # 这里简化实现，实际应该有购物车表
    # 直接创建订单
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': '商品不存在'}), 404

    return jsonify({'message': '添加成功'}), 200





@bp.route('/my_orders')
@login_required
def my_orders():
    # 获取筛选条件
    status = request.args.get('status', None)
    page = request.args.get('page', 1, type=int)

    # 查询用户订单，按创建时间降序
    query = Order.query.filter_by(user_id=current_user.id)
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    orders = pagination.items

    # 状态计数统计（全部状态）
    pending_count = Order.query.filter_by(user_id=current_user.id, status='pending').count()
    paid_count = Order.query.filter_by(user_id=current_user.id, status='paid').count()
    shipped_count = Order.query.filter_by(user_id=current_user.id, status='shipped').count()
    completed_count = Order.query.filter_by(user_id=current_user.id, status='completed').count()
    canceled_count = Order.query.filter_by(user_id=current_user.id, status='canceled').count()
    delivered_count = Order.query.filter_by(user_id=current_user.id, status='delivered').count()

    # 收藏和浏览历史数量统计
    favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    history_count = BrowsingHistory.query.filter_by(user_id=current_user.id).count()

    return render_template(
        'orders.html',
        orders=orders,
        pagination=pagination,
        current_status=status,
        pending_count=pending_count,
        paid_count=paid_count,
        shipped_count=shipped_count,
        delivered_count=delivered_count,
        completed_count=completed_count,
        canceled_count=canceled_count,
        favorites_count=favorites_count,
        history_count=history_count
    )


@bp.route('/add_review', methods=['POST'])
@login_required
def add_review():
    data = request.get_json()

    review = Review(
        user_id=current_user.id,
        product_id=data['product_id'],
        rating=data['rating'],
        comment=data.get('comment', '')
    )

    db.session.add(review)
    db.session.commit()

    return jsonify({'message': '评价添加成功'}), 201


@bp.route('/toggle_favorite', methods=['POST'])
@login_required
def toggle_favorite():
    data = request.get_json()
    product_id = data.get('product_id')
    if not product_id:
        return jsonify({'success': False, 'message': '缺少商品ID'}), 400

    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()

    if favorite:
        db.session.delete(favorite)
        action = 'removed'
    else:
        favorite = Favorite(
            user_id=current_user.id,
            product_id=product_id
        )
        db.session.add(favorite)
        action = 'added'

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'收藏已{ "添加" if action == "added" else "取消" }',
        'action': action,
        'product_id': product_id
    }), 200


@bp.route('/recommendations')
@login_required
def recommendations():
    # 这里会调用推荐引擎
    # 暂时返回热门商品
    recommended_products = Product.query.limit(10).all()

    return render_template('recommendations.html',
                           products=recommended_products)


# 商家功能
@bp.route('/merchant/dashboard/data')
@login_required
def merchant_dashboard_data():
    if not current_user.is_merchant():
        return jsonify({'success': False, 'message': '没有权限'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = 20
    category_id = request.args.get('category_id', type=int)
    query = Product.query.filter_by(merchant_id=current_user.id)
    if category_id:
        query = query.filter_by(category_id=category_id)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    result = []
    for p in products:
        result.append({
            'id': p.id,
            'category': p.category.name if p.category else '未分类',
            'name': p.name,
            'description': p.description,
            'image_url': p.image_url if p.image_url else '',
            'price': float(p.price),
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else ''
        })

    return jsonify({
        'success': True,
        'products': result,
        'pagination': {
            'page': pagination.page,
            'pages': pagination.pages,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@bp.route('/merchant/product/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    if not current_user.is_merchant():
        return jsonify({'success': False, 'message': '没有权限'}), 403

    product = Product.query.get_or_404(product_id)
    if product.merchant_id != current_user.id:
        return jsonify({'success': False, 'message': '不能修改他人商品'}), 403

    data = request.get_json()
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.price = data.get('price', product.price)
    product.image_url = data.get('image_url', product.image_url)
    product.category_id = data.get('category_id', product.category_id)
    db.session.commit()

    return jsonify({'success': True, 'message': '修改成功'})


@bp.route('/merchant/product/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    if not current_user.is_merchant():
        return jsonify({'success': False, 'message': '没有权限'}), 403

    product = Product.query.get_or_404(product_id)
    if product.merchant_id != current_user.id:
        return jsonify({'success': False, 'message': '不能删除他人商品'}), 403

    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True, 'message': '删除成功'})


@bp.route('/merchant/dashboard')
@login_required
def merchant_dashboard():
    if not current_user.is_merchant():
        return redirect(url_for('main.index'))

    # 商家的商品
    products = Product.query.filter_by(merchant_id=current_user.id).all()

    # 销售统计
    orders = db.session.query(Order).join(OrderItem).join(Product).filter(
        Product.merchant_id == current_user.id
    ).all()

    return render_template('merchant/dashboard.html',
                           products=products,
                           orders=orders)


@bp.route('/merchant/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_merchant():
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

        product = Product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            stock=data['stock'],
            category_id=data['category_id'],
            merchant_id=current_user.id,
            image_url=data.get('image_url', '')
        )

        db.session.add(product)
        db.session.commit()

        if request.is_json:
            return jsonify({'message': '商品添加成功', 'product_id': product.id}), 201

        return redirect(url_for('main.merchant_dashboard'))

    categories = Category.query.all()
    return render_template('merchant/add_product.html', categories=categories)

@bp.route('/search')
def search():
    query = request.args.get('q', '')
    results = Product.query.filter(Product.name.contains(query)).all()
    return render_template('search_results.html', products=results, query=query)


# 展示用户收藏商品列表
# @bp.route('/my_favorites')
# @login_required
# def my_favorites():
#     page = request.args.get('page', 1, type=int)
#     per_page = 10
#
#     favorites_query = Favorite.query.filter_by(user_id=current_user.id).join(Product).order_by(Favorite.created_at.desc())
#     pagination = favorites_query.paginate(page=page, per_page=per_page, error_out=False)
#     favorites = pagination.items
#
#     return render_template('favorites.html',
#                            favorites=favorites,
#                            pagination=pagination)

@bp.route('/favorites')
@login_required
def favorites():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    favorites_query = Favorite.query.filter_by(user_id=current_user.id).join(Product).order_by(
        Favorite.created_at.desc())
    pagination = favorites_query.paginate(page=page, per_page=per_page, error_out=False)
    favorites = pagination.items

    return render_template('favorites.html',
                           favorites=favorites,
                           pagination=pagination)

@bp.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = BrowsingHistory.query.filter_by(user_id=current_user.id).order_by(BrowsingHistory.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    histories = pagination.items
    return render_template('history.html', histories=histories, pagination=pagination)


# 清空当前用户所有浏览历史
@bp.route('/history/clear_all', methods=['DELETE'])
@login_required
def clear_all_history():
    BrowsingHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'success': True, 'message': '浏览历史已清空'}), 200

# 清除特定商品的浏览记录
@bp.route('/history/clear/<int:product_id>', methods=['POST'])
@login_required
def clear_history_item(product_id):
    print(current_user,current_user.id)
    history = BrowsingHistory.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    # print(product_id)
    print(history.id, history.user_id)
    if history:
        db.session.delete(history)
        db.session.commit()
        return jsonify({'success': True, 'message': '该商品浏览历史已删除'}), 200
    return jsonify({'success': False, 'message': '记录不存在'}), 404




# 用户个人资料页

@bp.route('/profile')
@login_required
def profile():
    order_stats = {
        'pending': Order.query.filter_by(user_id=current_user.id, status='待付款').count(),
        'confirmed': Order.query.filter_by(user_id=current_user.id, status='待确认').count(),
        'processing': Order.query.filter_by(user_id=current_user.id, status='进行中').count(),
        'completed': Order.query.filter_by(user_id=current_user.id, status='已完成').count()
    }
    orders_count = Order.query.filter_by(user_id=current_user.id).count()
    favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    history_count = BrowsingHistory.query.filter_by(user_id=current_user.id).count()
    return render_template('profile.html',
                           user=current_user,
                           order_stats=order_stats,
                           orders_count=orders_count,
                           favorites_count=favorites_count,
                           history_count=history_count)


# 购物车页面
@bp.route('/cart')
@login_required
def cart():
    # 由于未设计购物车模型，这里从最近未结算的订单模拟购物车
    latest_order = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).first()

    items = []
    if latest_order:
        items = OrderItem.query.filter_by(order_id=latest_order.id).all()

    return render_template('cart.html', items=items)

@bp.route('/merchant/categories')
@login_required
def merchant_categories():
    if not current_user.is_merchant():
        return jsonify({'success': False, 'message': '没有权限'}), 403

    categories = Category.query.all()
    result = [{'id': c.id, 'name': c.name} for c in categories]

    return jsonify({'success': True, 'categories': result})


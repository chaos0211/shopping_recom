from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.models.product import Product
from app.models.cart import Cart

# from app.models import CartItem, Product

bp = Blueprint('cart', __name__)

@bp.route('/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({'success': False, 'message': '缺少商品ID'}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': '商品不存在'}), 404

    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    return jsonify({'success': True, 'message': '已加入购物车'})


@bp.route('/', methods=['GET'])
@login_required
def cart_page():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', cart_items=items)

@bp.route('/delete/<int:product_id>', methods=['DELETE'])
@login_required
def delete_cart_item(product_id):
    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not item:
        return jsonify({'success': False, 'message': '商品不在购物车中'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': '已从购物车删除'})


@bp.route('/data', methods=['GET'])
@login_required
def cart_data():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    result = []
    for item in items:
        result.append({
            'product_id': item.product_id,
            'name': item.product.name,
            'image_url': item.product.image_url,
            'price': float(item.product.price),
            'quantity': item.quantity
        })
    return jsonify({'success': True, 'cart': result})

@bp.route('/clear', methods=['POST'])
@login_required
def clear_cart():
    Cart.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'success': True, 'message': '购物车已清空'})

@bp.route('/count', methods=['GET'])
@login_required
def cart_count():
    total_quantity = db.session.query(db.func.sum(Cart.quantity)) \
                        .filter(Cart.user_id == current_user.id).scalar() or 0
    return jsonify({'success': True, 'count': total_quantity})


@bp.route('/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart_item(product_id):
    data = request.get_json()
    quantity = data.get('quantity')

    if quantity is None or quantity < 1:
        return jsonify({'success': False, 'message': '无效的商品数量'}), 400

    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not item:
        return jsonify({'success': False, 'message': '购物车中没有该商品'}), 404

    item.quantity = quantity
    db.session.commit()

    return jsonify({'success': True, 'message': '数量已更新'})
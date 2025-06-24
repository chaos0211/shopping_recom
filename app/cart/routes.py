from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.models.order import Order, OrderItem
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

@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    data = request.get_json()
    selected_ids = data.get('items', [])

    if not selected_ids:
        return jsonify({'success': False, 'message': '未选择任何商品'}), 400

    cart_items = Cart.query.filter(
        Cart.user_id == current_user.id,
        Cart.product_id.in_(selected_ids)
    ).all()

    if not cart_items:
        return jsonify({'success': False, 'message': '购物车为空'}), 400

    total_amount = 0
    status = data.get('status', 'paid')  # 默认为 paid
    order = Order(user_id=current_user.id, total_amount=0, status=status)
    db.session.add(order)
    db.session.flush()

    for item in cart_items:
        product = Product.query.get(item.product_id)
        # if not product or product.stock < item.quantity:
        #     continue

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.price * item.quantity,
        )
        total_amount += product.price * item.quantity
        # product.stock -= item.quantity
        db.session.add(order_item)

    order.total_amount = total_amount
    db.session.commit()

    # 清空购物车中已结算的商品
    Cart.query.filter(
        Cart.user_id == current_user.id,
        Cart.product_id.in_(selected_ids)
    ).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '订单创建成功',
        'order_id': order.id,
        'total_amount': float(total_amount)
    }), 201

from decimal import Decimal

@bp.route('/total', methods=['GET'])
@login_required
def get_cart_total():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in items)
    shipping = Decimal('0.00')  # 固定运费，用 Decimal 保持一致
    total = subtotal + shipping
    return jsonify({
        'success': True,
        'subtotal': float(round(subtotal, 2)),
        'shipping': float(round(shipping, 2)),
        'total': float(round(total, 2))
    })
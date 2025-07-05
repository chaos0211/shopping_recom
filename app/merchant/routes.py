from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.order import Order, OrderItem
from app.models.product import Product

bp = Blueprint('merchant', __name__)


@bp.route('/overview')
@login_required
def merchant_overview():
    merchant_id = current_user.id  # 商家 ID

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # 总销售额
    total_revenue = db.session.query(db.func.sum(OrderItem.price))\
        .join(Product, OrderItem.product_id == Product.id)\
        .filter(Product.merchant_id == merchant_id)\
        .scalar() or 0

    # 总订单数（同一个订单可能包含多个商品，只计一次）
    total_orders = db.session.query(db.func.count(db.distinct(OrderItem.order_id)))\
        .join(Product, OrderItem.product_id == Product.id)\
        .filter(Product.merchant_id == merchant_id)\
        .scalar() or 0

    # 上架商品数
    active_products = db.session.query(Product.id)\
        .filter(Product.merchant_id == merchant_id).count()

    # 最近订单总数（用于分页）
    total_recent_orders = db.session.query(db.func.count(db.distinct(Order.id)))\
        .join(OrderItem, Order.id == OrderItem.order_id)\
        .join(Product, OrderItem.product_id == Product.id)\
        .filter(Product.merchant_id == merchant_id)\
        .scalar()

    total_pages = (total_recent_orders + per_page - 1) // per_page

    # 最近订单（按时间倒序分页）
    recent_orders = db.session.query(Order).distinct(Order.id)\
        .join(OrderItem, Order.id == OrderItem.order_id)\
        .join(Product, OrderItem.product_id == Product.id)\
        .filter(Product.merchant_id == merchant_id)\
        .order_by(Order.created_at.desc())\
        .offset((page - 1) * per_page).limit(per_page).all()

    recent_order_data = []
    for order in recent_orders:
        order_item = OrderItem.query.filter_by(order_id=order.id).first()
        product_name = Product.query.get(order_item.product_id).name if order_item else "未知"
        recent_order_data.append({
            "id": order.id,
            "product": product_name,
            "customer": order.user_id,
            "amount": f"{order.total_amount:.2f}",
            "status": order.status,
            "time": order.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return jsonify({
        "success": True,
        "stats": {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "active_products": active_products,
            "avg_rating": 4.5  # 后续支持真实评分计算
        },
        "recent_orders": recent_order_data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_recent_orders,
            "pages": total_pages,
            "has_more": page < total_pages
        }
    })
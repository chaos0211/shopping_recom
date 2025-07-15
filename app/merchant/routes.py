from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.order import Order, OrderItem
from app.models.product import Product
from sqlalchemy import func,select


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

@bp.route('/analytics')
def merchant_analytics():
    user_id = current_user.id

    # 查找该商户的商品
    product_ids = select(Product.id).where(Product.merchant_id == user_id)

    order_data = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(OrderItem.price).label('daily_revenue'),
        func.count(func.distinct(Order.id)).label('daily_orders')
    ).join(Order, OrderItem.order_id == Order.id) \
        .filter(OrderItem.product_id.in_(product_ids)) \
        .filter(Order.status == 'paid') \
        .group_by(func.date(Order.created_at)) \
        .order_by(func.date(Order.created_at)).all()

    labels = []
    revenue_data = []
    order_data_list = []

    for row in order_data:
        labels.append(row.date.strftime('%Y-%m-%d'))
        revenue_data.append(float(row.daily_revenue or 0))
        order_data_list.append(row.daily_orders)

    return jsonify({
        'success': True,
        'revenue_trend': {
            'labels': labels,
            'data': revenue_data
        },
        'orders_trend': {
            'labels': labels,
            'data': order_data_list
        }
    })
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app.models.product import Product
from app.models.order import Order
from spark_modules.recommendation_engine import RecommendationEngine
from spark_modules.sales_predictor import SalesPredictor
from spark_modules.data_preprocessor import DataPreprocessor
import json

bp = Blueprint('api', __name__)


@bp.route('/recommendations/<int:user_id>')
def get_recommendations(user_id):
    """获取用户推荐"""
    try:
        # 初始化推荐引擎
        rec_engine = RecommendationEngine()

        # 这里需要实际的数据预处理和模型训练
        # 暂时返回示例数据
        recommendations = [
            {'product_id': 1, 'score': 0.95, 'rank': 1},
            {'product_id': 2, 'score': 0.87, 'rank': 2},
            {'product_id': 3, 'score': 0.82, 'rank': 3}
        ]

        rec_engine.close()

        return jsonify({
            'user_id': user_id,
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/sales_prediction')
@login_required
def sales_prediction():
    """销售预测"""
    if not current_user.is_merchant():
        return jsonify({'error': '权限不足'}), 403

    try:
        predictor = SalesPredictor()

        # 示例预测结果
        predictions = [
            {'product_id': 1, 'predicted_sales': 150, 'confidence': 0.85},
            {'product_id': 2, 'predicted_sales': 89, 'confidence': 0.78}
        ]

        predictor.close()

        return jsonify({
            'predictions': predictions,
            'generated_at': '2025-06-19'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/analytics/overview')
@login_required
def analytics_overview():
    """数据分析概览"""
    if not current_user.is_merchant():
        return jsonify({'error': '权限不足'}), 403

    # 基本统计
    total_products = Product.query.filter_by(merchant_id=current_user.id).count()
    total_orders = Order.query.join(OrderItem).join(Product).filter(
        Product.merchant_id == current_user.id
    ).count()

    return jsonify({
        'total_products': total_products,
        'total_orders': total_orders,
        'revenue': 12500.00,  # 示例数据
        'avg_order_value': 125.00
    })


@bp.route('/similar_products/<int:product_id>')
def similar_products(product_id):
    """获取相似商品"""
    try:
        # 这里应该使用推荐引擎获取相似商品
        # 暂时返回同类别的其他商品
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': '商品不存在'}), 404

        similar = Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product_id
        ).limit(5).all()

        similar_list = [{
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'image_url': p.image_url
        } for p in similar]

        return jsonify({
            'product_id': product_id,
            'similar_products': similar_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/trending_products')
def trending_products():
    """获取趋势商品"""
    # 这里应该基于最近的交互数据计算趋势
    trending = Product.query.limit(10).all()

    trending_list = [{
        'id': p.id,
        'name': p.name,
        'price': float(p.price),
        'image_url': p.image_url,
        'trend_score': 0.8  # 示例分数
    } for p in trending]

    return jsonify({
        'trending_products': trending_list
    })

# 新增：用户资料更新接口
@bp.route('/update_profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户资料"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据无效'}), 400

        current_user.username = data.get('username', current_user.username)
        current_user.phone = data.get('phone', current_user.phone)
        current_user.email = data.get('email', current_user.email)
        current_user.address = data.get('address', current_user.address)

        from app import db
        db.session.commit()

        return jsonify({'success': True, 'message': '资料更新成功'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.models.recommend import Recommendation


bp = Blueprint('recommend', __name__)
@bp.route('/recommendations')
@login_required
def api_recommendations():
    recs = Recommendation.query.filter_by(user_id=current_user.id).order_by(Recommendation.score.desc()).limit(8).all()
    products = []
    for rec in recs:
        p = rec.product
        products.append({
            'id': p.id,
            'name': p.name,
            # 'brand': p.stock,
            'price': float(p.price),
            'rating': p.stock or 0,
            'image_url': p.image_url or '/static/images/default-product.jpg',
            'description': p.description or ''
        })
    return jsonify(products)
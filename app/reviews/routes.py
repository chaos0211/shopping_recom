from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models.review import Review

bp = Blueprint('reviews', __name__)


# 添加评价
@bp.route('/add', methods=['POST'])
@login_required
def add_review():
    data = request.get_json()
    product_id = data.get('product_id')
    rating = data.get('rating')
    comment = data.get('comment')

    if not product_id or not rating:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400

    review = Review(
        user_id=current_user.id,
        product_id=product_id,
        rating=rating,
        comment=comment,
        created_at=datetime.utcnow()
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({'success': True, 'message': '评价已添加'}), 201


# 获取某商品的所有评价
@bp.route('/product/<int:product_id>/reviews', methods=['GET'])
def get_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    data = [{
        'id': r.id,
        'user_id': r.user_id,
        'rating': r.rating,
        'comment': r.comment,
        'likes': r.likes,
        'created_at': r.created_at.isoformat()
    } for r in reviews]

    return jsonify({'success': True, 'reviews': data, 'count': len(reviews)}), 200


# 点赞评价
@bp.route('/<int:review_id>/like', methods=['POST'])
@login_required
def like_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.likes += 1
    db.session.commit()
    return jsonify({'success': True, 'message': '点赞成功', 'likes': review.likes}), 200


# 取消点赞评价
@bp.route('/<int:review_id>/dislike', methods=['POST'])
@login_required
def dislike_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.likes = max(0, review.likes - 1)
    db.session.commit()
    return jsonify({'success': True, 'message': '取消点赞成功', 'likes': review.likes}), 200

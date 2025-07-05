from app import db
from datetime import datetime


class Recommendation(db.Model):
    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    score = db.Column(db.Float, nullable=False, default=0.0)
    rank = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系（可选）
    user = db.relationship("User", backref="recommendations")
    product = db.relationship("Product", backref="recommended_to")

    def __repr__(self):
        return f'<Recommendation user_id={self.user_id} product_id={self.product_id} score={self.score}>'
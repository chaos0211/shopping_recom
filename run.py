from app import create_app, db

app = create_app()

from app.models.user import User
from app.models.product import Product, Category
from app.models.order import Order, OrderItem
from app.models.review import Review, Favorite, BrowsingHistory

with app.app_context():
    db.create_all()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Product': Product,
        'Category': Category,
        'Order': Order,
        'OrderItem': OrderItem,
        'Review': Review,
        'Favorite': Favorite,
        'BrowsingHistory': BrowsingHistory
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
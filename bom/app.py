from flask import Flask
from flask_cors import CORS

from .database import db

app = Flask(__name__)
CORS(app)

app.config.from_pyfile('config.py')
db.init_app(app)


# Импорт моделей BOM
from .models.product import Product
from .models.product_classifier import ProductClassifier
from .models.bom_position import BOMPosition
from .models.bom_change import BOMChange
from .models.unit import Unit


# Импорт API BOM
from .bom_routes import bom_bp

app.register_blueprint(bom_bp)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not Unit.query.first():
            db.session.add_all([
                Unit(short_name='шт', name='штуки'),
                Unit(short_name='кг', name='килограммы'),
                Unit(short_name='м', name='метры'),
                Unit(short_name='т', name='тонны')
            ])
            db.session.commit()

            print('База BOM создана и заполнена единицами измерения!')

    print('BOM запущен на http://127.0.0.1:5001')
    app.run(debug=False, port=5001)
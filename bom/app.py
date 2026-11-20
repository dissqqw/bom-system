from flask import Flask
from flask_cors import CORS

from .database import db

app = Flask(__name__)
CORS(app)
app.config.from_pyfile("config.py")
db.init_app(app)

# Существующие модели подсистемы BOM.
from .models.product import Product
from .models.product_classifier import ProductClassifier
from .models.bom_position import BOMPosition
from .models.bom_change import BOMChange
from .models.unit import Unit

# Модели маршрутной технологии. Импорт необходим до db.create_all().
from .models.product_operation import ProductOperation, PurchasePosition, RoutePosition
from .models.input_resource_position import InputResourcePosition
from .models.work_center import WorkCenter
from .models.operation_classifier import OperationClassifier
from .models.profession_classifier import ProfessionClassifier
from .models.tool_requirement import ToolRequirement

from .bom_routes import bom_bp
from .technology_routes import technology_bp

app.register_blueprint(bom_bp)
app.register_blueprint(technology_bp)


if __name__ == "__main__":
    with app.app_context():
        # Добавляет отсутствующие таблицы подсистемы маршрутной технологии.
        # Существующие таблицы products / BOM при этом не пересоздаются.
        db.create_all()

        if not Unit.query.first():
            db.session.add_all([
                Unit(short_name="шт", name="штуки"),
                Unit(short_name="кг", name="килограммы"),
                Unit(short_name="м", name="метры"),
                Unit(short_name="т", name="тонны"),
                Unit(short_name="л", name="литры"),
                Unit(short_name="компл", name="комплекты"),
            ])
            db.session.commit()
            print("База BOM создана и заполнена единицами измерения!")

    print("BOM + маршрутные технологии запущены на http://127.0.0.1:5001")
    app.run(debug=False, port=5001)

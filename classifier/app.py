
from flask import Flask
from flask_cors import CORS

from database import db

app = Flask(__name__)
CORS(app)

app.config.from_pyfile('config.py')
db.init_app(app)


# Импорт моделей классификатора
from models.car_class import CarClass, Car
from models.unit import Unit
from models.enumeration import Enumeration, EnumValue, ClassEnum, CarEnumValue
from models.parameter import (
    Parameter,
    ClassParameter,
    CarParameter,
    ParameterGroup
)
from models.ho import (
    EconomicEntity,
    HOClass,
    Role,
    HOClassRole,
    HOParameter,
    HOClassParameter,
    HOInstance,
    HOActor,
    HOParameterValue,
    HOPosition
)


# Импорт API классификатора
from api.class_routes import class_bp
from api.car_routes import car_bp
from api.enum_routes import enum_bp
from api.unit_routes import unit_bp
from api.parameter_routes import parameter_bp
from api.filter_routes import filter_bp
from api.ho_routes import ho_bp


# Регистрация маршрутов
app.register_blueprint(class_bp)
app.register_blueprint(car_bp)
app.register_blueprint(enum_bp)
app.register_blueprint(unit_bp)
app.register_blueprint(parameter_bp)
app.register_blueprint(filter_bp)
app.register_blueprint(ho_bp)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Начальное заполнение единиц измерения
        if not Unit.query.first():
            db.session.add_all([
                Unit(short_name='шт', name='штуки'),
                Unit(short_name='кг', name='килограммы'),
                Unit(short_name='м', name='метры'),
                Unit(short_name='т', name='тонны')
            ])
            db.session.commit()

        # Начальная категория классификатора
        if not CarClass.query.first():
            root = CarClass(
                name='Каталог Каршеринга',
                short_name='ROOT'
            )
            db.session.add(root)
            db.session.commit()

            print('База классификатора создана и заполнена тестовыми данными!')

    print('Classifier запущен на http://127.0.0.1:5000')
    app.run(debug=False, port=5000)

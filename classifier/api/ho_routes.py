"""REST API для хозяйственных операций."""
from datetime import date, datetime
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from database import db
from models.ho import (
    EconomicEntity, HOClass, Role, HOClassRole, HOParameter,
    HOClassParameter, HOInstance, HOActor, HOParameterValue, HOPosition,
)
from models.car_class import Car
from models.enumeration import Enumeration, EnumValue
from models.unit import Unit

ho_bp = Blueprint("ho", __name__)
VALUE_TYPES = {"numeric", "integer", "string", "datetime", "enum"}


def _json_error(message, status=400):
    # Roll back pending changes as well as return the validation error.
    db.session.rollback()
    return jsonify({"error": message}), status


def _save_or_error(obj, status=201):
    try:
        db.session.add(obj)
        db.session.commit()
        return jsonify(obj.to_dict()), status
    except IntegrityError:
        db.session.rollback()
        return _json_error("Запись с такими уникальными данными уже существует", 409)
    except Exception as exc:
        db.session.rollback()
        return _json_error(str(exc), 500)


def _operation_dict(ho):
    return {
        "ho": ho.to_dict(),
        "actors": [actor.to_dict() for actor in ho.actors],
        "parameters": [parameter.to_dict() for parameter in ho.parameter_values],
        "positions": [position.to_dict() for position in ho.positions],
    }


@ho_bp.route("/api/ho/entities", methods=["GET"])
def get_entities():
    items = EconomicEntity.query.order_by(EconomicEntity.name).all()
    return jsonify({"entities": [item.to_dict() for item in items], "count": len(items)})


@ho_bp.route("/api/ho/entities", methods=["POST"])
def add_entity():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return _json_error("Поле name обязательно")
    inn = str(data.get("inn", "")).strip() or None
    if inn and (not inn.isdigit() or len(inn) not in (10, 12)):
        return _json_error("ИНН должен содержать 10 или 12 цифр")
    entity = EconomicEntity(
        name=name,
        inn=inn,
        entity_type=data.get("entity_type") or "legal",
    )
    return _save_or_error(entity)


@ho_bp.route("/api/ho/roles", methods=["GET"])
def get_roles():
    items = Role.query.order_by(Role.name).all()
    return jsonify({"roles": [item.to_dict() for item in items], "count": len(items)})


@ho_bp.route("/api/ho/roles", methods=["POST"])
def add_role():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip()
    if not name or not code:
        return _json_error("Поля name и code обязательны")
    return _save_or_error(Role(name=name, code=code))


@ho_bp.route("/api/ho/parameters", methods=["GET"])
def get_ho_parameters():
    items = HOParameter.query.order_by(HOParameter.name).all()
    return jsonify({"parameters": [item.to_dict() for item in items], "count": len(items)})


@ho_bp.route("/api/ho/parameters", methods=["POST"])
def add_ho_parameter():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()
    name = str(data.get("name", "")).strip()
    value_type = data.get("value_type")
    if not code or not name or value_type not in VALUE_TYPES:
        return _json_error("Нужны code, name и корректный value_type")
    unit_id = data.get("unit_id") or None
    enum_id = data.get("enum_id") or None
    if unit_id is not None and not Unit.query.get(unit_id):
        return _json_error("Единица измерения не найдена", 404)
    if value_type == "enum":
        if enum_id is None or not Enumeration.query.get(enum_id):
            return _json_error("Для параметра типа enum нужно существующее enum_id")
    elif enum_id is not None and not Enumeration.query.get(enum_id):
        return _json_error("Перечисление не найдено", 404)
    return _save_or_error(HOParameter(
        code=code, name=name, value_type=value_type, unit_id=unit_id, enum_id=enum_id
    ))


@ho_bp.route("/api/ho/classes", methods=["GET"])
def get_ho_classes():
    items = HOClass.query.order_by(HOClass.name).all()
    return jsonify({"classes": [item.to_dict() for item in items], "count": len(items)})


@ho_bp.route("/api/ho/class/add", methods=["POST"])
def add_ho_class():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip()
    parent_id = data.get("parent_id") or None
    if not name or not code:
        return _json_error("Поля name и code обязательны")
    if parent_id is not None:
        parent = HOClass.query.get(parent_id)
        if not parent:
            return _json_error("Родительский класс не найден", 404)
    return _save_or_error(HOClass(name=name, code=code, parent_id=parent_id))


@ho_bp.route("/api/ho/class/<int:id_ho_class>/schema", methods=["GET"])
def get_ho_class_schema(id_ho_class):
    item = HOClass.query.get(id_ho_class)
    if not item:
        return _json_error("Класс хозяйственной операции не найден", 404)
    return jsonify({
        "class": item.to_dict(),
        "parameters": [link.to_dict() for link in item.parameter_links],
        "roles": [link.to_dict() for link in item.allowed_roles],
    })


@ho_bp.route("/api/ho/class/<int:id_ho_class>/parameter/link", methods=["POST"])
def link_ho_parameter(id_ho_class):
    data = request.get_json(silent=True) or {}
    if not HOClass.query.get(id_ho_class):
        return _json_error("Класс хозяйственной операции не найден", 404)
    id_param = data.get("id_param")
    parameter = HOParameter.query.get(id_param) if id_param else None
    if not parameter:
        return _json_error("Параметр хозяйственной операции не найден", 404)
    existing = HOClassParameter.query.filter_by(
        id_ho_class=id_ho_class, id_param=id_param
    ).first()
    if existing:
        return _json_error("Параметр уже привязан к классу")
    link = HOClassParameter(
        id_ho_class=id_ho_class,
        id_param=id_param,
        sort_order=data.get("sort_order", 0),
        min_value=data.get("min_value"),
        max_value=data.get("max_value"),
        is_required=bool(data.get("is_required", False)),
    )
    return _save_or_error(link)


@ho_bp.route("/api/ho/class/<int:id_ho_class>/role/link", methods=["POST"])
def link_ho_role(id_ho_class):
    data = request.get_json(silent=True) or {}
    if not HOClass.query.get(id_ho_class):
        return _json_error("Класс хозяйственной операции не найден", 404)
    id_role = data.get("id_role")
    if not id_role or not Role.query.get(id_role):
        return _json_error("Роль не найдена", 404)
    existing = HOClassRole.query.filter_by(
        id_ho_class=id_ho_class, id_role=id_role
    ).first()
    if existing:
        return _json_error("Роль уже привязана к классу")
    link = HOClassRole(
        id_ho_class=id_ho_class,
        id_role=id_role,
        is_required=bool(data.get("is_required", True)),
    )
    return _save_or_error(link)


@ho_bp.route("/api/ho/instance/add", methods=["POST"])
def add_ho_instance():
    data = request.get_json(silent=True) or {}
    id_ho_class = data.get("id_ho_class")
    if not id_ho_class:
        return _json_error("id_ho_class обязателен")
    if not HOClass.query.get(id_ho_class):
        return _json_error("Класс хозяйственной операции не найден", 404)
    doc_date = None
    if data.get("doc_date"):
        try:
            doc_date = date.fromisoformat(str(data["doc_date"]))
        except ValueError:
            return _json_error("doc_date должен иметь формат YYYY-MM-DD")
    try:
        amount = float(data["total_amount"]) if data.get("total_amount") not in (None, "") else 0.0
    except (ValueError, TypeError):
        return _json_error("total_amount должен быть числом")
    if amount < 0:
        return _json_error("total_amount не может быть отрицательным")
    item = HOInstance(
        id_ho_class=id_ho_class,
        doc_number=(str(data.get("doc_number", "")).strip() or None),
        doc_date=doc_date,
        total_amount=amount,
    )
    try:
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201
    except Exception as exc:
        db.session.rollback()
        return _json_error(str(exc), 500)


@ho_bp.route("/api/ho/instances", methods=["GET"])
def get_ho_instances():
    query = HOInstance.query
    id_ho_class = request.args.get("id_ho_class", type=int)
    if id_ho_class:
        query = query.filter_by(id_ho_class=id_ho_class)
    items = query.order_by(HOInstance.created_at.desc()).all()
    return jsonify({"instances": [_operation_dict(item) for item in items], "count": len(items)})


@ho_bp.route("/api/ho/<int:id_ho>/actor", methods=["PUT"])
def set_ho_actor(id_ho):
    data = request.get_json(silent=True) or {}
    item = HOInstance.query.get(id_ho)
    if not item:
        return _json_error("Хозяйственная операция не найдена", 404)
    id_role, id_sxd = data.get("id_role"), data.get("id_sxd")
    if not id_role or not id_sxd:
        return _json_error("id_role и id_sxd обязательны")
    role = Role.query.get(id_role)
    entity = EconomicEntity.query.get(id_sxd)
    if not role or not entity:
        return _json_error("Роль или субъект хозяйственной деятельности не найдены", 404)
    if not HOClassRole.query.filter_by(id_ho_class=item.id_ho_class, id_role=id_role).first():
        return _json_error("Эта роль не разрешена для выбранного класса операции")
    actor = HOActor.query.filter_by(id_ho=id_ho, id_role=id_role).first()
    if actor:
        actor.id_sxd = id_sxd
    else:
        actor = HOActor(id_ho=id_ho, id_role=id_role, id_sxd=id_sxd)
        db.session.add(actor)
    try:
        db.session.commit()
        return jsonify(actor.to_dict())
    except Exception as exc:
        db.session.rollback()
        return _json_error(str(exc), 500)


@ho_bp.route("/api/ho/<int:id_ho>/parameter", methods=["PUT"])
def set_ho_parameter_value(id_ho):
    data = request.get_json(silent=True) or {}
    item = HOInstance.query.get(id_ho)
    if not item:
        return _json_error("Хозяйственная операция не найдена", 404)
    id_param = data.get("id_param")
    parameter = HOParameter.query.get(id_param) if id_param else None
    if not parameter:
        return _json_error("Параметр не найден", 404)
    link = HOClassParameter.query.filter_by(
        id_ho_class=item.id_ho_class, id_param=id_param
    ).first()
    if not link:
        return _json_error("Параметр не привязан к классу этой операции")
    value = data.get("value")
    enum_value_id = data.get("enum_value_id")
    row = HOParameterValue.query.filter_by(id_ho=id_ho, id_param=id_param).first()
    if row is None:
        row = HOParameterValue(id_ho=id_ho, id_param=id_param)
        db.session.add(row)
    try:
        row.val_r = row.val_int = row.val_str = row.val_datetime = row.enum_val = None
        vt = parameter.value_type
        if vt == "numeric":
            if value in (None, ""):
                return _json_error("Для числового параметра нужно значение")
            number = float(value)
            if link.min_value is not None and number < link.min_value:
                return _json_error(f"Значение меньше минимума {link.min_value}")
            if link.max_value is not None and number > link.max_value:
                return _json_error(f"Значение больше максимума {link.max_value}")
            row.val_r = number
        elif vt == "integer":
            if value in (None, ""):
                return _json_error("Для целочисленного параметра нужно значение")
            number = int(value)
            if link.min_value is not None and number < link.min_value:
                return _json_error(f"Значение меньше минимума {link.min_value}")
            if link.max_value is not None and number > link.max_value:
                return _json_error(f"Значение больше максимума {link.max_value}")
            row.val_int = number
        elif vt == "string":
            if value is None:
                return _json_error("Для строкового параметра нужно значение")
            row.val_str = str(value)
        elif vt == "datetime":
            if not value:
                return _json_error("Для параметра даты нужно значение")
            row.val_datetime = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        elif vt == "enum":
            enum_value = EnumValue.query.get(enum_value_id) if enum_value_id else None
            if not enum_value or enum_value.id_enum != parameter.enum_id:
                return _json_error("Нужно выбрать значение связанного перечисления")
            row.enum_val = enum_value.id_value
        else:
            return _json_error("Неподдерживаемый тип параметра")
        db.session.commit()
        return jsonify(row.to_dict())
    except (ValueError, TypeError):
        db.session.rollback()
        return _json_error("Значение не соответствует типу параметра")
    except Exception as exc:
        db.session.rollback()
        return _json_error(str(exc), 500)


@ho_bp.route("/api/ho/<int:id_ho>/position/add", methods=["POST"])
def add_ho_position(id_ho):
    data = request.get_json(silent=True) or {}
    item = HOInstance.query.get(id_ho)
    if not item:
        return _json_error("Хозяйственная операция не найдена", 404)
    id_car = data.get("id_car")
    car = Car.query.get(id_car) if id_car else None
    if not car:
        return _json_error("Автомобиль не найден", 404)
    try:
        quantity = float(data.get("quantity", 1))
        price = float(data["price"]) if data.get("price") not in (None, "") else None
    except (ValueError, TypeError, KeyError):
        return _json_error("Количество и цена должны быть числами")
    if quantity <= 0 or (price is not None and price < 0):
        return _json_error("Количество должно быть больше нуля, цена — неотрицательной")
    position = HOPosition(
        id_ho=id_ho,
        id_car=id_car,
        quantity=quantity,
        price=price,
        amount=quantity * price if price is not None else 0.0,
    )
    try:
        db.session.add(position)
        db.session.flush()
        item.total_amount = db.session.query(db.func.coalesce(db.func.sum(HOPosition.amount), 0)).filter_by(id_ho=id_ho).scalar()
        db.session.commit()
        return jsonify(position.to_dict()), 201
    except Exception as exc:
        db.session.rollback()
        return _json_error(str(exc), 500)


@ho_bp.route("/api/ho/class/<int:id_ho_class>/find", methods=["GET"])
def find_ho_by_class(id_ho_class):
    if not HOClass.query.get(id_ho_class):
        return _json_error("Класс хозяйственной операции не найден", 404)
    items = HOInstance.query.filter_by(id_ho_class=id_ho_class).order_by(HOInstance.created_at.desc()).all()
    result = [_operation_dict(item) for item in items]
    return jsonify({"ho_instances": result, "count": len(result)})

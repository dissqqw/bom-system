"""HTTP API подсистемы управления маршрутными технологиями."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from .database import db
from .models.input_resource_position import InputResourcePosition
from .models.operation_classifier import OperationClassifier
from .models.product import Product
from .models.product_operation import (
    ProductOperation,
    PurchasePosition,
    Qualification,
    RoutePosition,
)
from .models.profession_classifier import ProfessionClassifier
from .models.tool_requirement import ToolRequirement
from .models.unit import Unit
from .models.work_center import WorkCenter
from .services.technology_calculations import (
    CALCULATE_TM_COST,
    FIND_TM,
    MR_Q,
    SUM_MR,
    TR_TO,
)

technology_bp = Blueprint("technology", __name__)


def _error(message, status=400):
    db.session.rollback()
    return jsonify({"error": message}), status


def _json_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Ожидается JSON-объект")
    return data


def _required_id(data, key):
    value = data.get(key)
    if isinstance(value, bool):
        raise ValueError(f"Поле {key} должно быть целым числом")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Поле {key} должно быть целым числом")
    if result <= 0:
        raise ValueError(f"Поле {key} должно быть больше нуля")
    return result


def _positive_decimal(value, field_name, allow_zero=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Поле {field_name} должно быть числом")

    min_is_valid = result >= 0 if allow_zero else result > 0
    if not result.is_finite() or not min_is_valid:
        phrase = "не может быть отрицательным" if allow_zero else "должно быть больше нуля"
        raise ValueError(f"Поле {field_name} {phrase}")
    return result


def _get_or_404(model, object_id, label):
    obj = db.session.get(model, object_id)
    if obj is None:
        raise LookupError(f"{label} с id={object_id} не найден(а)")
    return obj


def _request_quantity():
    raw = request.args.get("quantity", "1")
    return _positive_decimal(raw, "quantity")


def _would_create_cycle(out_to_id, in_to_id):
    """Проверяет, появится ли цикл при добавлении out_to -> in_to."""
    if out_to_id == in_to_id:
        return True

    visited = set()
    stack = [in_to_id]

    while stack:
        current_id = stack.pop()
        if current_id == out_to_id:
            return True
        if current_id in visited:
            continue
        visited.add(current_id)

        edges = InputResourcePosition.query.filter_by(
            out_to_id=current_id
        ).all()
        stack.extend(edge.in_to_id for edge in edges)

    return False


def _calculation_response(function, *args):
    try:
        return jsonify(function(*args)), 200
    except LookupError as exc:
        return _error(str(exc), 404)
    except ValueError as exc:
        return _error(str(exc), 400)


# ------------------------------------------------------------------
# Справочники: ГРЦ, классы операций и профессии
# ------------------------------------------------------------------

@technology_bp.route("/api/tm/work-centers", methods=["GET"])
def get_work_centers():
    items = WorkCenter.query.order_by(WorkCenter.name).all()
    return jsonify({"work_centers": [item.to_dict() for item in items]}), 200


@technology_bp.route("/api/tm/work-centers", methods=["POST"])
def add_work_center():
    try:
        data = _json_data()
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Поле name обязательно")
        rate = data.get("hourly_rate")
        item = WorkCenter(
            name=name,
            hourly_rate=(
                _positive_decimal(rate, "hourly_rate", allow_zero=True)
                if rate is not None else None
            ),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "created", "work_center": item.to_dict()}), 201
    except ValueError as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error("Рабочий центр с таким названием уже существует", 409)


@technology_bp.route("/api/tm/operation-classes", methods=["GET"])
def get_operation_classes():
    items = OperationClassifier.query.order_by(OperationClassifier.name).all()
    return jsonify({"operation_classes": [item.to_dict() for item in items]}), 200


@technology_bp.route("/api/tm/operation-classes", methods=["POST"])
def add_operation_class():
    try:
        data = _json_data()
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Поле name обязательно")
        parent_id = data.get("parent_id")
        if parent_id is not None:
            parent_id = int(parent_id)
            _get_or_404(OperationClassifier, parent_id, "Родительский класс")
        item = OperationClassifier(name=name, parent_id=parent_id)
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "created", "operation_class": item.to_dict()}), 201
    except LookupError as exc:
        return _error(str(exc), 404)
    except (ValueError, TypeError) as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error("Класс операции с таким названием уже существует", 409)


@technology_bp.route("/api/tm/professions", methods=["GET"])
def get_professions():
    items = ProfessionClassifier.query.order_by(ProfessionClassifier.name).all()
    return jsonify({"professions": [item.to_dict() for item in items]}), 200


@technology_bp.route("/api/tm/professions", methods=["POST"])
def add_profession():
    try:
        data = _json_data()
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Поле name обязательно")
        rate = data.get("hourly_rate")
        item = ProfessionClassifier(
            name=name,
            hourly_rate=(
                _positive_decimal(rate, "hourly_rate", allow_zero=True)
                if rate is not None else None
            ),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "created", "profession": item.to_dict()}), 201
    except ValueError as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error("Профессия с таким названием уже существует", 409)


# ------------------------------------------------------------------
# Создание позиций маршрутной технологии
# ------------------------------------------------------------------

@technology_bp.route("/api/tm/route-positions", methods=["POST"])
def add_route_position():
    try:
        data = _json_data()
        product_id = _required_id(data, "product_id")
        sequence_number = _required_id(data, "sequence_number")
        work_center_id = _required_id(data, "work_center_id")
        operation_class_id = _required_id(data, "operation_class_id")
        profession_class_id = _required_id(data, "profession_class_id")

        _get_or_404(Product, product_id, "Изделие")
        work_center = _get_or_404(WorkCenter, work_center_id, "ГРЦ")
        operation_class = _get_or_404(
            OperationClassifier, operation_class_id, "Класс операции"
        )
        profession = _get_or_404(
            ProfessionClassifier, profession_class_id, "Профессия"
        )

        qualification_raw = str(data.get("qualification", "")).strip()
        try:
            qualification = Qualification(qualification_raw)
        except ValueError:
            allowed = ", ".join(item.value for item in Qualification)
            raise ValueError(f"qualification должна быть одним из значений: {allowed}")

        setup_time = _positive_decimal(
            data.get("setup_time", 0), "setup_time", allow_zero=True
        )
        unit_time = _positive_decimal(
            data.get("unit_time", 0), "unit_time", allow_zero=True
        )

        item = RoutePosition(
            product_id=product_id,
            sequence_number=sequence_number,
            setup_time=setup_time,
            unit_time=unit_time,
            work_center=work_center,
            operation_class=operation_class,
            profession=profession,
            qualification=qualification,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "created", "route_position": item.to_dict()}), 201
    except LookupError as exc:
        return _error(str(exc), 404)
    except (ValueError, TypeError) as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error(
            "Не удалось создать позицию: проверьте уникальность номера операции",
            409,
        )


@technology_bp.route("/api/tm/purchase-positions", methods=["POST"])
def add_purchase_position():
    try:
        data = _json_data()
        product_id = _required_id(data, "product_id")
        sequence_number = _required_id(data, "sequence_number")
        _get_or_404(Product, product_id, "Изделие")

        raw_price = data.get("purchase_price")
        purchase_price = (
            _positive_decimal(raw_price, "purchase_price", allow_zero=True)
            if raw_price is not None else None
        )

        item = PurchasePosition(
            product_id=product_id,
            sequence_number=sequence_number,
            purchase_price=purchase_price,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "created", "purchase_position": item.to_dict()}), 201
    except LookupError as exc:
        return _error(str(exc), 404)
    except (ValueError, TypeError) as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error(
            "Не удалось создать позицию закупки: номер позиции уже занят",
            409,
        )


@technology_bp.route("/api/tm/input-resources", methods=["POST"])
def add_input_resource():
    try:
        data = _json_data()
        out_to_id = _required_id(data, "out_to_id")
        in_to_id = _required_id(data, "in_to_id")
        unit_id = _required_id(data, "unit_id")
        consumer = _get_or_404(RoutePosition, out_to_id, "Операция-потребитель")
        source = _get_or_404(ProductOperation, in_to_id, "Позиция-источник")
        unit = _get_or_404(Unit, unit_id, "Единица измерения")

        if _would_create_cycle(out_to_id, in_to_id):
            raise ValueError("Связь создаёт циклическую зависимость")

        consumption = _positive_decimal(data.get("consumption"), "consumption")
        for_quantity = _positive_decimal(
            data.get("for_quantity", 1), "for_quantity"
        )

        duplicate = InputResourcePosition.query.filter_by(
            out_to_id=consumer.id_to,
            in_to_id=source.id_to,
        ).first()
        if duplicate:
            return _error("Такая входная позиция уже добавлена", 409)

        item = InputResourcePosition(
            out_to=consumer,
            in_to=source,
            consumption=consumption,
            for_quantity=for_quantity,
            unit=unit,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "created", "input_resource": item.to_dict()}), 201
    except LookupError as exc:
        return _error(str(exc), 404)
    except (ValueError, TypeError) as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error("Не удалось создать входной ресурс", 409)


@technology_bp.route("/api/tm/tool-requirements", methods=["POST"])
def add_tool_requirement():
    try:
        data = _json_data()
        route_position_id = _required_id(data, "route_position_id")
        product_id = _required_id(data, "product_id")
        quantity = _positive_decimal(data.get("quantity", 1), "quantity")

        route_position = _get_or_404(
            RoutePosition, route_position_id, "Технологическая операция"
        )
        product = _get_or_404(Product, product_id, "Инструмент/оснастка")

        item = ToolRequirement(
            route_position=route_position,
            product=product,
            quantity=quantity,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "created", "tool_requirement": item.to_dict()}), 201
    except LookupError as exc:
        return _error(str(exc), 404)
    except (ValueError, TypeError) as exc:
        return _error(str(exc))


# ------------------------------------------------------------------
# Поиск маршрута и расчётные функции задания
# ------------------------------------------------------------------

@technology_bp.route("/api/tm/product/<int:pIdEl>/route", methods=["GET"])
def find_technology_route(pIdEl):
    return _calculation_response(FIND_TM, pIdEl)


@technology_bp.route(
    "/api/tm/operation/<int:pIdTO>/resources", methods=["GET"]
)
def calculate_operation_resources(pIdTO):
    try:
        quantity = _request_quantity()
        return _calculation_response(MR_Q, pIdTO, quantity)
    except ValueError as exc:
        return _error(str(exc))


@technology_bp.route(
    "/api/tm/product/<int:pIdEl>/materials", methods=["GET"]
)
def calculate_product_materials(pIdEl):
    try:
        quantity = _request_quantity()
        return _calculation_response(SUM_MR, pIdEl, quantity)
    except ValueError as exc:
        return _error(str(exc))


@technology_bp.route(
    "/api/tm/product/<int:pIdEl>/labor", methods=["GET"]
)
def calculate_product_labor(pIdEl):
    try:
        quantity = _request_quantity()
        return _calculation_response(TR_TO, pIdEl, quantity)
    except ValueError as exc:
        return _error(str(exc))


@technology_bp.route(
    "/api/tm/product/<int:pIdEl>/cost", methods=["GET"]
)
def calculate_product_cost(pIdEl):
    try:
        quantity = _request_quantity()
        return _calculation_response(CALCULATE_TM_COST, pIdEl, quantity)
    except ValueError as exc:
        return _error(str(exc))

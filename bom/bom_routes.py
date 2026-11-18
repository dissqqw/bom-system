
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .database import db
from .models.bom_change import BOMChange
from .models.bom_position import BOMPosition
from .models.product import Product
from .models.product_classifier import ProductClassifier
from .models.unit import Unit

bom_bp = Blueprint('bom', __name__)

PRODUCT_TYPES = {'material', 'part', 'assembly', 'complex'}


# ============================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================

class ApiError(Exception):
    """Ошибка валидации, которая превращается в JSON-ответ."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _json_error(message, status=400):
    """Возвращает JSON с ошибкой и отменяет незавершённые изменения."""
    db.session.rollback()
    return jsonify({'error': message}), status


@bom_bp.errorhandler(ApiError)
def _handle_api_error(exc):
    return _json_error(exc.message, exc.status)


def _clean_str(value):
    """None -> '', всё остальное -> str без пробелов по краям."""
    if value is None:
        return ''
    return str(value).strip()


def _clean_author(value):
    author = _clean_str(value)
    return author[:100] or None


def _parse_id(value, field_name):
    if isinstance(value, bool):
        raise ApiError(f'{field_name} должен быть целым числом')

    if isinstance(value, float):
        if not value.is_integer():
            raise ApiError(f'{field_name} должен быть целым числом')
        return int(value)

    try:
        return int(value)
    except (ValueError, TypeError):
        raise ApiError(f'{field_name} должен быть целым числом')


def _parse_positive_number(value, field_name):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ApiError(f'{field_name} должно быть числом')

    if not number.is_finite() or number <= 0:
        raise ApiError(f'{field_name} должно быть больше нуля')

    return number


def _parse_price(value):
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ApiError('Цена должна быть числом')

    if not price.is_finite():
        raise ApiError('Цена должна быть числом')

    if price < 0:
        raise ApiError('Цена не может быть отрицательной')

    return price


def _parse_bool_arg(name, default=True):
    raw = request.args.get(name)

    if raw is None:
        return default

    raw = raw.strip().lower()

    if raw in ('1', 'true', 'yes'):
        return True

    if raw in ('0', 'false', 'no'):
        return False

    raise ApiError(f'{name} должен иметь значение true или false')


def _check_product_type(value):
    if not isinstance(value, str) or value not in PRODUCT_TYPES:
        raise ApiError(
            'product_type должен быть material, part, assembly или complex'
        )
    return value


def _get_or_404(model, object_id, message):
    obj = db.session.get(model, object_id)

    if obj is None:
        raise ApiError(message, 404)

    return obj


def _get_json_object():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise ApiError('Ожидается JSON-объект')

    return data


def _register_bom_change(product_id, description, author=None):
    db.session.add(BOMChange(
        product_id=product_id,
        description=description,
        author=author
    ))


def _classifier_ids_with_children(classifier):
    """id классификатора и всех его потомков."""
    return {classifier.id_classifier} | {
        child.id_classifier for child in classifier.get_all_children()
    }


# ============================================================
# КЛАССИФИКАТОР ПРОДУКЦИИ
# ============================================================

@bom_bp.route('/api/bom/classifiers', methods=['GET'])
def get_classifiers():
    classifiers = ProductClassifier.query.order_by(
        ProductClassifier.name
    ).all()

    return jsonify({
        'classifiers': [item.to_dict() for item in classifiers],
        'count': len(classifiers)
    }), 200


@bom_bp.route('/api/bom/classifier/add', methods=['POST'])
def add_classifier():
    data = request.get_json(silent=True) or {}

    name = _clean_str(data.get('name'))
    parent_id = data.get('parent_id')

    if not name:
        return _json_error('Поле name обязательно')

    if parent_id is not None:
        parent_id = _parse_id(parent_id, 'parent_id')
        _get_or_404(
            ProductClassifier,
            parent_id,
            'Родительская категория не найдена'
        )

    classifier = ProductClassifier(
        name=name,
        parent_id=parent_id
    )

    try:
        db.session.add(classifier)
        db.session.commit()

        return jsonify({
            'status': 'created',
            'classifier': classifier.to_dict()
        }), 201

    except IntegrityError:
        return _json_error(
            'Не удалось создать категорию: ошибка целостности данных',
            409
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return _json_error(f'Внутренняя ошибка: {e}', 500)


@bom_bp.route('/api/bom/classifier/<int:id_classifier>', methods=['GET'])
def get_classifier(id_classifier):
    classifier = _get_or_404(
        ProductClassifier,
        id_classifier,
        'Категория не найдена'
    )

    return jsonify(classifier.to_dict()), 200


@bom_bp.route(
    '/api/bom/classifier/<int:id_classifier>/tree',
    methods=['GET']
)
def get_classifier_tree(id_classifier):
    classifier = ProductClassifier.query.options(
        selectinload(ProductClassifier.children)
    ).filter_by(id_classifier=id_classifier).first()

    if not classifier:
        return _json_error('Категория не найдена', 404)

    def build_tree(node):
        return {
            'id_classifier': node.id_classifier,
            'name': node.name,
            'parent_id': node.parent_id,
            'children': [
                build_tree(child) for child in node.children
            ]
        }

    return jsonify({'tree': build_tree(classifier)}), 200


# ============================================================
# СПРАВОЧНИК ИЗДЕЛИЙ
# ============================================================

def _check_base_product(base_product_id, product=None):
    base = _get_or_404(
        Product,
        base_product_id,
        'Базовое изделие не найдено'
    )

    if product is not None:
        if base.id_product == product.id_product:
            raise ApiError('Изделие не может быть базой самого себя')

        has_modifications = Product.query.filter_by(
            base_product_id=product.id_product
        ).first() is not None

        if has_modifications:
            raise ApiError(
                'У изделия есть модификации, поэтому оно не может '
                'само быть модификацией'
            )

    if base.base_product_id is not None:
        raise ApiError(
            'Базовое изделие само является модификацией. '
            'Модификацию можно создавать только на основе базового изделия'
        )

    return base


@bom_bp.route('/api/bom/products', methods=['GET'])
def get_products():
    query = Product.query

    classifier_id = request.args.get('classifier_id')
    product_type = request.args.get('product_type')
    include_subclasses = _parse_bool_arg(
        'include_subclasses',
        False
    )

    if classifier_id is not None:
        classifier_id = _parse_id(
            classifier_id,
            'classifier_id'
        )

        if include_subclasses:
            classifier = _get_or_404(
                ProductClassifier,
                classifier_id,
                'Классификатор не найден'
            )

            query = query.filter(
                Product.classifier_id.in_(
                    _classifier_ids_with_children(classifier)
                )
            )
        else:
            query = query.filter_by(
                classifier_id=classifier_id
            )

    if product_type is not None:
        _check_product_type(product_type)
        query = query.filter_by(product_type=product_type)

    products = query.order_by(Product.name).all()

    return jsonify({
        'products': [product.to_dict() for product in products],
        'count': len(products)
    }), 200


@bom_bp.route('/api/bom/product/<int:id_product>', methods=['GET'])
def get_product(id_product):
    product = _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    return jsonify(product.to_dict()), 200


@bom_bp.route('/api/bom/product/add', methods=['POST'])
def add_product():
    data = request.get_json(silent=True) or {}

    name = _clean_str(data.get('name'))
    designation = _clean_str(data.get('designation'))
    base_product_id = data.get('base_product_id')
    price = data.get('price')

    if not name:
        return _json_error('Поле name обязательно')

    if not designation:
        return _json_error('Поле designation обязательно')

    product_type = _check_product_type(
        data.get('product_type')
    )

    classifier_id = _parse_id(
        data.get('classifier_id'),
        'classifier_id'
    )

    _get_or_404(
        ProductClassifier,
        classifier_id,
        'Классификатор не найден'
    )

    if base_product_id is not None:
        base_product_id = _parse_id(
            base_product_id,
            'base_product_id'
        )
        _check_base_product(base_product_id)

    if price is not None:
        price = _parse_price(price)

    product = Product(
        name=name,
        designation=designation,
        product_type=product_type,
        classifier_id=classifier_id,
        base_product_id=base_product_id,
        price=price
    )

    try:
        db.session.add(product)
        db.session.commit()

        return jsonify({
            'status': 'created',
            'product': product.to_dict()
        }), 201

    except IntegrityError:
        return _json_error(
            'Не удалось создать изделие. Возможно, обозначение уже существует.',
            409
        )

    except Exception:
        return _json_error(
            'Внутренняя ошибка при создании изделия',
            500
        )


@bom_bp.route('/api/bom/product/<int:id_product>', methods=['PUT'])
def update_product(id_product):
    product = _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    data = _get_json_object()

    if 'name' in data:
        name = _clean_str(data['name'])

        if not name:
            return _json_error('Название не может быть пустым')

        product.name = name

    if 'designation' in data:
        designation = _clean_str(data['designation'])

        if not designation:
            return _json_error('Обозначение не может быть пустым')

        product.designation = designation

    if 'product_type' in data:
        new_type = _check_product_type(data['product_type'])

        if new_type == 'material':
            has_positions = BOMPosition.query.filter_by(
                parent_product_id=id_product
            ).first() is not None

            if has_positions:
                return _json_error(
                    'У изделия есть спецификация, оно не может быть материалом'
                )

        product.product_type = new_type

    if 'classifier_id' in data:
        classifier_id = _parse_id(
            data['classifier_id'],
            'classifier_id'
        )

        _get_or_404(
            ProductClassifier,
            classifier_id,
            'Классификатор не найден'
        )

        product.classifier_id = classifier_id

    if 'base_product_id' in data:
        base_product_id = data['base_product_id']

        if base_product_id is None:
            product.base_product_id = None
        else:
            base_product_id = _parse_id(
                base_product_id,
                'base_product_id'
            )

            _check_base_product(base_product_id, product)
            product.base_product_id = base_product_id

    if 'price' in data:
        product.price = (
            None
            if data['price'] is None
            else _parse_price(data['price'])
        )

    try:
        db.session.commit()

        return jsonify({
            'status': 'updated',
            'product': product.to_dict()
        }), 200

    except IntegrityError:
        return _json_error(
            'Не удалось обновить изделие. Возможно, обозначение уже занято.',
            409
        )

    except Exception:
        return _json_error(
            'Внутренняя ошибка при обновлении изделия',
            500
        )


# ============================================================
# ПОЗИЦИИ СПЕЦИФИКАЦИИ
# ============================================================

def _would_create_bom_cycle(parent_id, component_id):
    if parent_id == component_id:
        return True

    visited = set()
    stack = [component_id]

    while stack:
        current_id = stack.pop()

        if current_id == parent_id:
            return True

        if current_id in visited:
            continue

        visited.add(current_id)

        positions = BOMPosition.query.filter_by(
            parent_product_id=current_id
        ).all()

        for position in positions:
            stack.append(position.component_product_id)

    return False


def _visible_positions(product, include_base=True):
    query = BOMPosition.query.filter_by(
        parent_product_id=product.id_product
    )

    if not include_base and product.base_product_id is not None:
        query = query.filter_by(is_base=False)

    return query.order_by(
        BOMPosition.id_position
    ).all()


def _has_bom(product_id):
    return BOMPosition.query.filter_by(
        parent_product_id=product_id
    ).first() is not None


@bom_bp.route(
    '/api/bom/product/<int:id_product>/positions',
    methods=['GET']
)
def get_bom_positions(id_product):
    product = _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    include_base = _parse_bool_arg('include_base', True)
    positions = _visible_positions(product, include_base)

    return jsonify({
        'product': product.to_dict(),
        'positions': [
            position.to_dict() for position in positions
        ],
        'count': len(positions)
    }), 200


@bom_bp.route('/api/bom/position/add', methods=['POST'])
def add_bom_position():
    data = _get_json_object()

    parent_id = _parse_id(
        data.get('parent_product_id'),
        'parent_product_id'
    )

    component_id = _parse_id(
        data.get('component_product_id'),
        'component_product_id'
    )

    unit_id = _parse_id(
        data.get('unit_id'),
        'unit_id'
    )

    parent = _get_or_404(
        Product,
        parent_id,
        'Основное изделие не найдено'
    )

    component = _get_or_404(
        Product,
        component_id,
        'Компонент не найден'
    )

    _get_or_404(
        Unit,
        unit_id,
        'Единица измерения не найдена'
    )

    if parent.product_type == 'material':
        return _json_error(
            'Материал не может иметь собственную спецификацию'
        )

    if _would_create_bom_cycle(parent_id, component_id):
        return _json_error(
            'Добавление компонента создаст циклическую спецификацию'
        )

    duplicate = BOMPosition.query.filter_by(
        parent_product_id=parent_id,
        component_product_id=component_id
    ).first()

    if duplicate is not None:
        return _json_error(
            f'Компонент уже есть в спецификации (id_position='
            f'{duplicate.id_position}). Измените существующую позицию',
            409
        )

    consumption = _parse_positive_number(
        data.get('consumption'),
        'consumption'
    )

    for_quantity = _parse_positive_number(
        data.get('for_quantity', 1),
        'for_quantity'
    )

    is_base = data.get(
        'is_base',
        parent.base_product_id is None
    )

    if not isinstance(is_base, bool):
        return _json_error(
            'is_base должен иметь значение true или false'
        )

    author = _clean_author(data.get('author'))

    position = BOMPosition(
        parent_product_id=parent_id,
        component_product_id=component_id,
        consumption=consumption,
        for_quantity=for_quantity,
        is_base=is_base,
        unit_id=unit_id
    )

    try:
        db.session.add(position)

        _register_bom_change(
            parent_id,
            f'Добавлен компонент {component.designation} '
            f'в спецификацию изделия {parent.designation}',
            author
        )

        db.session.commit()

        return jsonify({
            'status': 'created',
            'position': position.to_dict()
        }), 201

    except Exception:
        return _json_error(
            'Не удалось добавить позицию спецификации',
            500
        )


@bom_bp.route(
    '/api/bom/position/<int:id_position>',
    methods=['PUT']
)
def update_bom_position(id_position):
    position = _get_or_404(
        BOMPosition,
        id_position,
        'Позиция спецификации не найдена'
    )

    data = _get_json_object()

    parent = position.parent_product
    changes = []
    content_changed = False

    if 'component_product_id' in data:
        component_id = _parse_id(
            data['component_product_id'],
            'component_product_id'
        )

        new_component = _get_or_404(
            Product,
            component_id,
            'Компонент не найден'
        )

        if component_id != position.component_product_id:
            if _would_create_bom_cycle(
                position.parent_product_id,
                component_id
            ):
                return _json_error(
                    'Замена компонента создаст циклическую спецификацию'
                )

            duplicate = BOMPosition.query.filter(
                BOMPosition.parent_product_id
                == position.parent_product_id,
                BOMPosition.component_product_id == component_id,
                BOMPosition.id_position != position.id_position
            ).first()

            if duplicate is not None:
                return _json_error(
                    'Такой компонент уже есть в спецификации',
                    409
                )

            changes.append(
                f'компонент {position.component_product.designation} '
                f'заменён на {new_component.designation}'
            )

            position.component_product_id = component_id
            content_changed = True

    if 'consumption' in data:
        value = _parse_positive_number(
            data['consumption'],
            'consumption'
        )

        changes.append(
            f'норма расхода {position.consumption} -> {value}'
        )

        position.consumption = value
        content_changed = True

    if 'for_quantity' in data:
        value = _parse_positive_number(
            data['for_quantity'],
            'for_quantity'
        )

        changes.append(
            f'на количество {position.for_quantity} -> {value}'
        )

        position.for_quantity = value
        content_changed = True

    if 'unit_id' in data:
        unit_id = _parse_id(
            data['unit_id'],
            'unit_id'
        )

        _get_or_404(
            Unit,
            unit_id,
            'Единица измерения не найдена'
        )

        if unit_id != position.unit_id:
            changes.append(
                f'единица измерения {position.unit_id} -> {unit_id}'
            )

            position.unit_id = unit_id
            content_changed = True

    if 'is_base' in data:
        if not isinstance(data['is_base'], bool):
            return _json_error(
                'is_base должен иметь значение true или false'
            )

        position.is_base = data['is_base']

    elif content_changed and parent.base_product_id is not None:
        position.is_base = False

    if not changes and 'is_base' not in data:
        return _json_error('Нет данных для изменения')

    if 'is_base' in data:
        changes.append(f'is_base = {position.is_base}')

    try:
        _register_bom_change(
            position.parent_product_id,
            f'Изменена позиция спецификации id={position.id_position}: '
            + '; '.join(changes),
            _clean_author(data.get('author'))
        )

        db.session.commit()

        return jsonify({
            'status': 'updated',
            'position': position.to_dict()
        }), 200

    except Exception:
        return _json_error(
            'Не удалось обновить позицию спецификации',
            500
        )


@bom_bp.route(
    '/api/bom/position/<int:id_position>',
    methods=['DELETE']
)
def delete_bom_position(id_position):
    position = _get_or_404(
        BOMPosition,
        id_position,
        'Позиция спецификации не найдена'
    )

    data = request.get_json(silent=True) or {}

    author = (
        _clean_author(data.get('author'))
        if isinstance(data, dict)
        else None
    )

    parent_id = position.parent_product_id
    component = position.component_product

    component_name = (
        component.designation
        if component is not None
        else str(position.component_product_id)
    )

    try:
        db.session.delete(position)

        _register_bom_change(
            parent_id,
            f'Удалён компонент {component_name} '
            f'из спецификации изделия id={parent_id}',
            author
        )

        db.session.commit()

        return jsonify({
            'status': 'deleted',
            'id_position': id_position
        }), 200

    except Exception:
        return _json_error(
            'Не удалось удалить позицию спецификации',
            500
        )


# ============================================================
# ПОЛНОЕ ДЕРЕВО СОСТАВА
# ============================================================

def _build_bom_tree(product, include_base, path=None):
    path = path or set()

    if product.id_product in path:
        raise ApiError('Обнаружен цикл в спецификации')

    current_path = path | {product.id_product}
    children = []

    for position in _visible_positions(product, include_base):
        component = position.component_product

        if component is None:
            raise ApiError(
                f'Компонент id={position.component_product_id} не найден'
            )

        child_tree = _build_bom_tree(
            component,
            include_base,
            current_path
        )

        child_tree['position'] = position.to_dict()
        children.append(child_tree)

    return {
        'product': product.to_dict(),
        'children': children
    }


@bom_bp.route(
    '/api/bom/product/<int:id_product>/tree',
    methods=['GET']
)
def find_bom(id_product):
    """FIND_BOM: рекурсивно строит полное дерево состава изделия."""

    product = _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    include_base = _parse_bool_arg('include_base', True)

    return jsonify({
        'include_base': include_base,
        'tree': _build_bom_tree(product, include_base)
    }), 200


@bom_bp.route(
    '/api/bom/product/<int:id_product>/components',
    methods=['GET']
)
def get_all_bom_components(id_product):
    """Плоский список компонентов на всю глубину вложенности."""

    product = _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    include_base = _parse_bool_arg('include_base', True)

    components = []

    def traverse(current, path, level):
        if current.id_product in path:
            raise ApiError('Обнаружен цикл в спецификации')

        current_path = path | {current.id_product}

        for position in _visible_positions(current, include_base):
            component = position.component_product

            if component is None:
                continue

            components.append({
                'level': level,
                'parent_product_id': current.id_product,
                'position': position.to_dict(),
                'product': component.to_dict()
            })

            traverse(
                component,
                current_path,
                level + 1
            )

    traverse(product, set(), 1)

    return jsonify({
        'product': product.to_dict(),
        'include_base': include_base,
        'components': components,
        'count': len(components)
    }), 200


# ============================================================
# РАСЧЁТ СОСТАВА И СТОИМОСТИ BOM
# ============================================================

def _calculate_bom(product, quantity, include_base, class_ids,
                   result, skipped, path=None):
    """
    Рекурсивно раскрывает спецификацию изделия.

    Учитывает конечные материалы и детали.
    Для сборочных единиц и комплексов раскрывает их спецификации.
    """

    path = path or set()

    if product.id_product in path:
        raise ApiError('Обнаружен цикл в спецификации')

    current_path = path | {product.id_product}

    for position in _visible_positions(product, include_base):
        component = position.component_product

        if component is None:
            raise ApiError(
                f'Компонент id={position.component_product_id} не найден'
            )

        required = (
            quantity
            * Decimal(str(position.consumption))
            / Decimal(str(position.for_quantity))
        )

        # Если компонент имеет собственную спецификацию,
        # раскрываем её вместо подсчёта самого компонента.
        if _has_bom(component.id_product):
            _calculate_bom(
                component,
                required,
                include_base,
                class_ids,
                result,
                skipped,
                current_path
            )
            continue

        # Учитываем конечные материалы и детали.
        if component.product_type not in ('material', 'part'):
            skipped[component.id_product] = {
                'product_id': component.id_product,
                'designation': component.designation,
                'product_type': component.product_type,
                'reason': (
                    'у изделия нет спецификации и оно '
                    'не является учитываемым компонентом'
                )
            }
            continue

        # Фильтрация по классификатору.
        if (
            class_ids is not None
            and component.classifier_id not in class_ids
        ):
            continue

        key = (
            component.classifier_id,
            component.id_product,
            position.unit_id
        )

        if key not in result:
            unit_price = (
                Decimal(str(component.price))
                if component.price is not None
                else None
            )

            result[key] = {
                'product_id': component.id_product,
                'name': component.name,
                'designation': component.designation,
                'product_type': component.product_type,
                'classifier_id': component.classifier_id,
                'unit_id': position.unit_id,
                'quantity': Decimal('0'),
                'unit_price': unit_price,
                'total_cost': None
            }

        item = result[key]

        # Суммируем количество компонента.
        item['quantity'] += required

        # Рассчитываем стоимость компонента.
        if item['unit_price'] is not None:
            item['total_cost'] = (
                item['quantity'] * item['unit_price']
            )
        else:
            item['total_cost'] = None


@bom_bp.route(
    '/api/bom/product/<int:id_product>/calculate',
    methods=['GET']
)
def calc_bom(id_product):
    """
    CALC_BOM: расчёт состава и стоимости компонентов изделия.

    Параметры:
      quantity      - количество изделий (по умолчанию 1);
      classifier_id - считать компоненты указанного класса и подклассов;
      include_base  - для модификаций:
                      true - вся спецификация,
                      false - только собственные позиции.
    """

    product = _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    quantity = _parse_positive_number(
        request.args.get('quantity', '1'),
        'quantity'
    )

    include_base = _parse_bool_arg('include_base', True)

    # Фильтр по классификатору.
    class_ids = None
    classifier_filter = None

    raw_classifier = request.args.get('classifier_id')

    if raw_classifier is not None:
        classifier_id = _parse_id(
            raw_classifier,
            'classifier_id'
        )

        classifier = _get_or_404(
            ProductClassifier,
            classifier_id,
            'Классификатор не найден'
        )

        class_ids = _classifier_ids_with_children(classifier)
        classifier_filter = classifier.to_dict()

    # Собираем компоненты.
    result = {}
    skipped = {}

    _calculate_bom(
        product,
        quantity,
        include_base,
        class_ids,
        result,
        skipped
    )

    # Формируем список ресурсов.
    resources = []

    for _, item in sorted(result.items()):
        resources.append({
            'product_id': item['product_id'],
            'name': item['name'],
            'designation': item['designation'],
            'product_type': item['product_type'],
            'classifier_id': item['classifier_id'],
            'unit_id': item['unit_id'],
            'quantity': float(item['quantity']),
            'unit_price': (
                str(item['unit_price'].quantize(Decimal('0.01')))
                if item['unit_price'] is not None
                else None
            ),
            'total_cost': (
                str(item['total_cost'].quantize(Decimal('0.01')))
                if item['total_cost'] is not None
                else None
            )
        })

    # Проверяем, есть ли компоненты без цены.
    has_missing_prices = any(
        item['unit_price'] is None
        for item in result.values()
    )

    # Считаем общую стоимость всех компонентов.
    total_component_cost = sum(
        (
            item['total_cost']
            for item in result.values()
            if item['total_cost'] is not None
        ),
        Decimal('0')
    )

    # Сводка по классификаторам и единицам измерения.
    summary = {}

    for item in result.values():
        key = (
            item['classifier_id'],
            item['unit_id']
        )

        summary[key] = (
            summary.get(key, Decimal('0'))
            + item['quantity']
        )

    # Получаем названия классификаторов.
    classifier_names = {
        c.id_classifier: c.name
        for c in ProductClassifier.query.filter(
            ProductClassifier.id_classifier.in_(
                {key[0] for key in summary}
            )
        ).all()
    } if summary else {}

    summary_by_class = [
        {
            'classifier_id': classifier_id,
            'classifier_name': classifier_names.get(classifier_id),
            'unit_id': unit_id,
            'quantity': float(total)
        }
        for (classifier_id, unit_id), total in sorted(summary.items())
    ]

    # Общая сумма не показывается как полная,
    # если у какого-либо компонента отсутствует цена.
    total_component_cost_result = (
        None
        if has_missing_prices
        else str(total_component_cost.quantize(Decimal('0.01')))
    )

    return jsonify({
        'product': product.to_dict(),
        'requested_quantity': float(quantity),
        'include_base': include_base,
        'classifier_filter': classifier_filter,
        'summary_by_class': summary_by_class,
        'resources': resources,
        'count': len(resources),
        'total_component_cost': total_component_cost_result,
        'has_missing_prices': has_missing_prices,
        'skipped': list(skipped.values())
    }), 200


# ============================================================
# СОЗДАНИЕ МОДИФИКАЦИИ
# ============================================================

@bom_bp.route(
    '/api/bom/product/<int:id_base>/modification',
    methods=['POST']
)
def create_modification(id_base):
    """CREATE_MODIFICATION: новая модификация + копия базовой спецификации."""

    base_product = _get_or_404(
        Product,
        id_base,
        'Базовое изделие не найдено'
    )

    if base_product.base_product_id is not None:
        return _json_error(
            'Изделие само является модификацией. '
            'Модификацию можно создавать только на основе базового изделия'
        )

    data = request.get_json(silent=True) or {}

    name = _clean_str(data.get('name'))

    if not name:
        return _json_error('Поле name обязательно')

    designation = _clean_str(data.get('designation'))

    if not designation:
        designation = (
            f'{base_product.designation}-MOD-{uuid4().hex[:8].upper()}'
        )

    modification = Product(
        name=name,
        designation=designation,
        product_type=base_product.product_type,
        classifier_id=base_product.classifier_id,
        base_product_id=base_product.id_product,
        price=base_product.price
    )

    try:
        db.session.add(modification)
        db.session.flush()

        # Копируется только базовая часть спецификации.
        base_positions = BOMPosition.query.filter_by(
            parent_product_id=base_product.id_product,
            is_base=True
        ).all()

        for position in base_positions:
            db.session.add(BOMPosition(
                parent_product_id=modification.id_product,
                component_product_id=position.component_product_id,
                consumption=position.consumption,
                for_quantity=position.for_quantity,
                is_base=True,
                unit_id=position.unit_id
            ))

        _register_bom_change(
            modification.id_product,
            f'Создана модификация на основе изделия '
            f'{base_product.designation}',
            _clean_author(data.get('author'))
        )

        db.session.commit()

        return jsonify({
            'status': 'created',
            'product': modification.to_dict(),
            'base_product_id': base_product.id_product,
            'copied_positions': len(base_positions)
        }), 201

    except IntegrityError:
        return _json_error(
            'Не удалось создать модификацию: обозначение уже занято',
            409
        )

    except Exception:
        return _json_error(
            'Ошибка при создании модификации',
            500
        )


# ============================================================
# ИСТОРИЯ ИЗМЕНЕНИЙ
# ============================================================

@bom_bp.route(
    '/api/bom/product/<int:id_product>/changes',
    methods=['GET']
)
def get_bom_changes(id_product):
    product = _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    changes = BOMChange.query.filter_by(
        product_id=id_product
    ).order_by(
        BOMChange.created_at.desc(),
        BOMChange.id_change.desc()
    ).all()

    return jsonify({
        'product': product.to_dict(),
        'changes': [change.to_dict() for change in changes],
        'count': len(changes)
    }), 200


@bom_bp.route(
    '/api/bom/product/<int:id_product>/changes',
    methods=['POST']
)
def register_change(id_product):
    """REGISTER_CHANGE: фиксация факта изменения спецификации."""

    _get_or_404(
        Product,
        id_product,
        'Изделие не найдено'
    )

    data = request.get_json(silent=True) or {}

    description = _clean_str(data.get('description'))

    if not description:
        return _json_error('Поле description обязательно')

    change = BOMChange(
        product_id=id_product,
        description=description,
        author=_clean_author(data.get('author'))
    )

    try:
        db.session.add(change)
        db.session.commit()

        return jsonify({
            'status': 'created',
            'change': change.to_dict()
        }), 201

    except Exception:
        return _json_error(
            'Не удалось зарегистрировать изменение',
            500
        )

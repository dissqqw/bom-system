from ..database import db


class Product(db.Model):
    __tablename__ = 'products'

    id_product = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False)
    designation = db.Column(db.String(100), unique=True, nullable=False)

    product_type = db.Column(db.String(30), nullable=False)

    classifier_id = db.Column(
        db.Integer,
        db.ForeignKey('product_classifiers.id_classifier'),
        nullable=False
    )

    base_product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id_product'),
        nullable=True
    )

    price = db.Column(db.Numeric(12, 2), nullable=True)

    classifier = db.relationship(
        'ProductClassifier',
        backref='products'
    )

    base_product = db.relationship(
        'Product',
        remote_side=[id_product],
        foreign_keys=[base_product_id],
        backref=db.backref('modifications', lazy='select')
    )

    # Маршрутные позиции изделия (добавлено для практической работы №6).
    technology_positions = db.relationship(
        'ProductOperation',
        back_populates='product',
        cascade='all, delete-orphan',
        order_by='ProductOperation.sequence_number',
    )

    def get_operations(self):
        """Возвращает технологические позиции изделия по порядку."""
        return list(self.technology_positions)

    def to_dict(self):
        return {
            'id_product': self.id_product,
            'name': self.name,
            'designation': self.designation,
            'product_type': self.product_type,
            'classifier_id': self.classifier_id,
            'base_product_id': self.base_product_id,
            'price': (
                float(self.price)
                if self.price is not None
                else None
            )
        }

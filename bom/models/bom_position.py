
from ..database import db


class BOMPosition(db.Model):
    __tablename__ = 'bom_positions'

    id_position = db.Column(db.Integer, primary_key=True)

    parent_product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id_product'),
        nullable=False
    )

    component_product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id_product'),
        nullable=False
    )

    consumption = db.Column(db.Numeric(12, 4), nullable=False)

    for_quantity = db.Column(
        db.Numeric(12, 4),
        nullable=False,
        default=1
    )

    is_base = db.Column(db.Boolean, nullable=False, default=True)

    unit_id = db.Column(
        db.Integer,
        db.ForeignKey('ei.id_ei'),
        nullable=False
    )

    parent_product = db.relationship(
        'Product',
        foreign_keys=[parent_product_id],
        backref=db.backref('bom_positions', lazy='select')
    )

    component_product = db.relationship(
        'Product',
        foreign_keys=[component_product_id],
        backref=db.backref('used_in_bom_positions', lazy='select')
    )

    unit = db.relationship(
        'Unit',
        backref=db.backref('bom_positions', lazy='select')
    )

    def to_dict(self):
        return {
            'id_position': self.id_position,
            'parent_product_id': self.parent_product_id,
            'component_product_id': self.component_product_id,
            'consumption': float(self.consumption),
            'for_quantity': float(self.for_quantity),
            'is_base': self.is_base,
            'unit_id': self.unit_id
        }

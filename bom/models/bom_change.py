
from datetime import datetime, timezone

from ..database import db


class BOMChange(db.Model):
    __tablename__ = 'bom_changes'

    id_change = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id_product'),
        nullable=False
    )

    description = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    author = db.Column(db.String(100), nullable=True)

    product = db.relationship(
        'Product',
        backref=db.backref('bom_changes', lazy='select')
    )

    def to_dict(self):
        return {
            'id_change': self.id_change,
            'product_id': self.product_id,
            'description': self.description,
            'created_at': (
                self.created_at.isoformat()
                if self.created_at is not None
                else None
            ),
            'author': self.author
        }

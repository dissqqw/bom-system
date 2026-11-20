from ..database import db


class OperationClassifier(db.Model):
    """Классификатор технологических операций с поддержкой иерархии."""

    __tablename__ = "tm_operation_classifiers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_operation_classifiers.id"),
        nullable=True,
    )

    parent = db.relationship(
        "OperationClassifier",
        remote_side=[id],
        backref=db.backref("children", lazy="select"),
    )
    route_positions = db.relationship(
        "RoutePosition",
        back_populates="operation_class",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
        }

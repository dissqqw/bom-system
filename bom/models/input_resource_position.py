from ..database import db


class InputResourcePosition(db.Model):
    """Связь между операцией-потребителем и операцией-источником ресурса.

    out_to_id — операция, которая расходует ресурс.
    in_to_id  — позиция, результат которой используется как ресурс.
    """

    __tablename__ = "tm_input_resources"

    id = db.Column(db.Integer, primary_key=True)
    out_to_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_product_operations.id_to"),
        nullable=False,
        index=True,
    )
    in_to_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_product_operations.id_to"),
        nullable=False,
        index=True,
    )
    consumption = db.Column(db.Numeric(12, 4), nullable=False)
    for_quantity = db.Column(
        db.Numeric(12, 4), nullable=False, default=1
    )
    unit_id = db.Column(
        db.Integer,
        db.ForeignKey("ei.id_ei"),
        nullable=False,
    )

    out_to = db.relationship(
        "ProductOperation",
        foreign_keys=[out_to_id],
        back_populates="input_resources",
    )
    in_to = db.relationship(
        "ProductOperation",
        foreign_keys=[in_to_id],
        back_populates="used_as_input_by",
    )
    unit = db.relationship("Unit")

    __table_args__ = (
        db.UniqueConstraint(
            "out_to_id", "in_to_id", name="uq_tm_input_resource_pair"
        ),
        db.CheckConstraint("consumption > 0", name="ck_tm_consumption_positive"),
        db.CheckConstraint("for_quantity > 0", name="ck_tm_for_quantity_positive"),
    )

    def required_quantity(self, output_quantity):
        """Количество ресурса для заданного объёма результата операции."""
        from decimal import Decimal

        q = Decimal(str(output_quantity))
        return (
            q * Decimal(str(self.consumption))
            / Decimal(str(self.for_quantity))
        )

    def to_dict(self):
        return {
            "id": self.id,
            "out_to_id": self.out_to_id,
            "in_to_id": self.in_to_id,
            "consumption": str(self.consumption),
            "for_quantity": str(self.for_quantity),
            "unit_id": self.unit_id,
            "unit_short_name": self.unit.short_name if self.unit else None,
            "source_position": self.in_to.to_dict() if self.in_to else None,
        }

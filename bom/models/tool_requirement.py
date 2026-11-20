from ..database import db


class ToolRequirement(db.Model):
    """Требование к инструменту или технологической оснастке."""

    __tablename__ = "tm_tool_requirements"

    id = db.Column(db.Integer, primary_key=True)
    route_position_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_route_positions.id_to"),
        nullable=False,
        index=True,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id_product"),
        nullable=False,
    )
    quantity = db.Column(db.Numeric(12, 4), nullable=False, default=1)

    route_position = db.relationship(
        "RoutePosition",
        back_populates="tool_requirements",
    )
    product = db.relationship("Product")

    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_tm_tool_quantity_positive"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "route_position_id": self.route_position_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_designation": (
                self.product.designation if self.product else None
            ),
            "quantity": str(self.quantity),
        }

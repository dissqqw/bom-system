from enum import Enum

from ..database import db


class Qualification(str, Enum):
    """Квалификационные разряды, требуемые для выполнения операции."""

    Grade1 = "Grade1"
    Grade2 = "Grade2"
    Grade3 = "Grade3"
    Grade4 = "Grade4"
    Grade5 = "Grade5"
    Grade6 = "Grade6"


class ProductOperation(db.Model):
    """Общая позиция изделия в технологическом графе.

    Используется как базовый класс для PurchasePosition и RoutePosition.
    В БД реализовано наследование с отдельными таблицами для подклассов.
    """

    __tablename__ = "tm_product_operations"

    id_to = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id_product"),
        nullable=False,
        index=True,
    )
    sequence_number = db.Column(db.Integer, nullable=False)
    position_type = db.Column(db.String(20), nullable=False)

    product = db.relationship(
        "Product",
        back_populates="technology_positions",
    )

    # out_to: эта позиция потребляет входные ресурсы.
    input_resources = db.relationship(
        "InputResourcePosition",
        foreign_keys="InputResourcePosition.out_to_id",
        back_populates="out_to",
        cascade="all, delete-orphan",
        order_by="InputResourcePosition.id",
    )

    # in_to: результат этой позиции используется другими операциями.
    used_as_input_by = db.relationship(
        "InputResourcePosition",
        foreign_keys="InputResourcePosition.in_to_id",
        back_populates="in_to",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "product_id",
            "sequence_number",
            name="uq_tm_product_sequence",
        ),
        db.CheckConstraint(
            "sequence_number > 0",
            name="ck_tm_sequence_positive",
        ),
    )

    __mapper_args__ = {
        "polymorphic_on": position_type,
        "polymorphic_identity": "base",
    }

    def get_input_resources(self):
        """Возвращает ресурсы, которые потребляет данная позиция."""
        return list(self.input_resources)

    def to_dict(self):
        return {
            "id_to": self.id_to,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_designation": (
                self.product.designation if self.product else None
            ),
            "sequence_number": self.sequence_number,
            "position_type": self.position_type,
        }


class PurchasePosition(ProductOperation):
    """Позиция закупки: готовый компонент, не проходящий обработку."""

    __tablename__ = "tm_purchase_positions"

    id_to = db.Column(
        db.Integer,
        db.ForeignKey("tm_product_operations.id_to", ondelete="CASCADE"),
        primary_key=True,
    )
    purchase_price = db.Column(db.Numeric(12, 2), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "purchase",
    }

    def effective_price(self):
        """Цена позиции закупки; если не задана, берётся Product.price."""
        if self.purchase_price is not None:
            return self.purchase_price
        return self.product.price if self.product else None

    def to_dict(self):
        result = super().to_dict()
        price = self.effective_price()
        result.update({
            "purchase_price": str(price) if price is not None else None,
        })
        return result


class RoutePosition(ProductOperation):
    """Позиция собственного технологического маршрута."""

    __tablename__ = "tm_route_positions"

    id_to = db.Column(
        db.Integer,
        db.ForeignKey("tm_product_operations.id_to", ondelete="CASCADE"),
        primary_key=True,
    )
    setup_time = db.Column(
        db.Numeric(12, 4), nullable=False, default=0
    )
    unit_time = db.Column(
        db.Numeric(12, 4), nullable=False, default=0
    )
    work_center_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_work_centers.id_grc"),
        nullable=False,
    )
    operation_class_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_operation_classifiers.id"),
        nullable=False,
    )
    profession_class_id = db.Column(
        db.Integer,
        db.ForeignKey("tm_profession_classifiers.id"),
        nullable=False,
    )
    qualification = db.Column(
        db.Enum(Qualification, native_enum=False, name="tm_qualification"),
        nullable=False,
    )

    work_center = db.relationship(
        "WorkCenter",
        back_populates="route_positions",
    )
    operation_class = db.relationship(
        "OperationClassifier",
        back_populates="route_positions",
    )
    profession = db.relationship(
        "ProfessionClassifier",
        back_populates="route_positions",
    )
    tool_requirements = db.relationship(
        "ToolRequirement",
        back_populates="route_position",
        cascade="all, delete-orphan",
        order_by="ToolRequirement.id",
    )

    __mapper_args__ = {
        "polymorphic_identity": "route",
    }

    def calculate_labor(self, quantity):
        """Трудоёмкость партии: Тпз + Q * Тшт.

        Время хранится в часах. Подготовительно-заключительное время
        учитывается один раз на партию данной операции.
        """
        from decimal import Decimal

        q = Decimal(str(quantity))
        return Decimal(str(self.setup_time)) + q * Decimal(str(self.unit_time))

    def to_dict(self):
        result = super().to_dict()
        result.update({
            "setup_time": str(self.setup_time),
            "unit_time": str(self.unit_time),
            "work_center_id": self.work_center_id,
            "work_center_name": (
                self.work_center.name if self.work_center else None
            ),
            "operation_class_id": self.operation_class_id,
            "operation_class_name": (
                self.operation_class.name if self.operation_class else None
            ),
            "profession_class_id": self.profession_class_id,
            "profession_name": (
                self.profession.name if self.profession else None
            ),
            "qualification": (
                self.qualification.value
                if isinstance(self.qualification, Qualification)
                else str(self.qualification)
            ),
            "tool_requirements": [
                item.to_dict() for item in self.tool_requirements
            ],
        })
        return result

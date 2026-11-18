"""Модели хозяйственных операций (дополнение к классификатору каршеринга)."""
from datetime import datetime
from database import db


class EconomicEntity(db.Model):
    __tablename__ = "economic_entities"

    id_sxd = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    inn = db.Column(db.String(12), unique=True)
    entity_type = db.Column(db.String(20), default="legal")

    def to_dict(self):
        return {
            "id_sxd": self.id_sxd,
            "name": self.name,
            "inn": self.inn,
            "entity_type": self.entity_type,
        }


class HOClass(db.Model):
    __tablename__ = "ho_classes"

    id_ho_class = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("ho_classes.id_ho_class"))

    parent = db.relationship(
        "HOClass",
        backref=db.backref("children", lazy="select"),
        remote_side=[id_ho_class],
    )

    def to_dict(self):
        return {
            "id_ho_class": self.id_ho_class,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
        }


class Role(db.Model):
    __tablename__ = "roles"

    id_role = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)

    def to_dict(self):
        return {"id_role": self.id_role, "name": self.name, "code": self.code}


class HOClassRole(db.Model):
    __tablename__ = "ho_class_roles"

    id_ho_class = db.Column(
        db.Integer, db.ForeignKey("ho_classes.id_ho_class"), primary_key=True
    )
    id_role = db.Column(db.Integer, db.ForeignKey("roles.id_role"), primary_key=True)
    is_required = db.Column(db.Boolean, default=True, nullable=False)

    ho_class = db.relationship("HOClass", backref=db.backref("allowed_roles", lazy="select"))
    role = db.relationship("Role", backref=db.backref("class_links", lazy="select"))

    def to_dict(self):
        return {
            "id_ho_class": self.id_ho_class,
            "id_role": self.id_role,
            "role": self.role.to_dict() if self.role else None,
            "is_required": self.is_required,
        }


class HOParameter(db.Model):
    __tablename__ = "ho_parameters"

    id_param = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    value_type = db.Column(db.String(20), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("ei.id_ei"))
    enum_id = db.Column(db.Integer, db.ForeignKey("enumerations.id_enum"))

    unit = db.relationship("Unit")
    enumeration = db.relationship("Enumeration")

    def to_dict(self):
        return {
            "id_param": self.id_param,
            "code": self.code,
            "name": self.name,
            "value_type": self.value_type,
            "unit_id": self.unit_id,
            "unit": self.unit.to_dict() if self.unit else None,
            "enum_id": self.enum_id,
            "enumeration": self.enumeration.to_dict() if self.enumeration else None,
        }


class HOClassParameter(db.Model):
    __tablename__ = "ho_class_parameters"

    id_ho_class = db.Column(
        db.Integer, db.ForeignKey("ho_classes.id_ho_class"), primary_key=True
    )
    id_param = db.Column(
        db.Integer, db.ForeignKey("ho_parameters.id_param"), primary_key=True
    )
    sort_order = db.Column(db.Integer, default=0)
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    is_required = db.Column(db.Boolean, default=False)

    ho_class = db.relationship("HOClass", backref=db.backref("parameter_links", lazy="select"))
    parameter = db.relationship("HOParameter", backref=db.backref("class_links", lazy="select"))

    def to_dict(self):
        return {
            "id_ho_class": self.id_ho_class,
            "id_param": self.id_param,
            "parameter": self.parameter.to_dict() if self.parameter else None,
            "sort_order": self.sort_order,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "is_required": self.is_required,
        }


class HOInstance(db.Model):
    __tablename__ = "ho_instances"

    id_ho = db.Column(db.Integer, primary_key=True)
    id_ho_class = db.Column(
        db.Integer, db.ForeignKey("ho_classes.id_ho_class"), nullable=False
    )
    doc_number = db.Column(db.String(50))
    doc_date = db.Column(db.Date)
    total_amount = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    ho_class = db.relationship("HOClass")
    actors = db.relationship("HOActor", back_populates="ho", cascade="all, delete-orphan")
    parameter_values = db.relationship(
        "HOParameterValue", back_populates="ho", cascade="all, delete-orphan"
    )
    positions = db.relationship("HOPosition", back_populates="ho", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id_ho": self.id_ho,
            "id_ho_class": self.id_ho_class,
            "ho_class": self.ho_class.to_dict() if self.ho_class else None,
            "doc_number": self.doc_number,
            "doc_date": self.doc_date.isoformat() if self.doc_date else None,
            "total_amount": self.total_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HOActor(db.Model):
    __tablename__ = "ho_actors"

    id_ho = db.Column(
        db.Integer, db.ForeignKey("ho_instances.id_ho"), primary_key=True
    )
    id_role = db.Column(db.Integer, db.ForeignKey("roles.id_role"), primary_key=True)
    id_sxd = db.Column(db.Integer, db.ForeignKey("economic_entities.id_sxd"), nullable=False)

    ho = db.relationship("HOInstance", back_populates="actors")
    sxd = db.relationship("EconomicEntity")
    role = db.relationship("Role")

    def to_dict(self):
        return {
            "id_ho": self.id_ho,
            "id_role": self.id_role,
            "role": self.role.to_dict() if self.role else None,
            "id_sxd": self.id_sxd,
            "entity": self.sxd.to_dict() if self.sxd else None,
        }


class HOParameterValue(db.Model):
    __tablename__ = "ho_parameter_values"

    id_ho = db.Column(
        db.Integer, db.ForeignKey("ho_instances.id_ho"), primary_key=True
    )
    id_param = db.Column(
        db.Integer, db.ForeignKey("ho_parameters.id_param"), primary_key=True
    )
    val_r = db.Column(db.Float)
    val_int = db.Column(db.Integer)
    val_str = db.Column(db.String(255))
    val_datetime = db.Column(db.DateTime)
    enum_val = db.Column(db.Integer, db.ForeignKey("enum_values.id_value"))

    ho = db.relationship("HOInstance", back_populates="parameter_values")
    parameter = db.relationship("HOParameter")
    enum_value = db.relationship("EnumValue", foreign_keys=[enum_val])

    def value(self):
        if not self.parameter:
            return None
        value_type = self.parameter.value_type
        if value_type == "numeric":
            return self.val_r
        if value_type == "integer":
            return self.val_int
        if value_type == "string":
            return self.val_str
        if value_type == "datetime":
            return self.val_datetime.isoformat() if self.val_datetime else None
        if value_type == "enum":
            return self.enum_value.to_dict() if self.enum_value else None
        return None

    def to_dict(self):
        return {
            "id_ho": self.id_ho,
            "id_param": self.id_param,
            "parameter": self.parameter.to_dict() if self.parameter else None,
            "value": self.value(),
        }


class HOPosition(db.Model):
    __tablename__ = "ho_positions"

    id_position = db.Column(db.Integer, primary_key=True)
    id_ho = db.Column(
        db.Integer, db.ForeignKey("ho_instances.id_ho"), nullable=False
    )
    id_car = db.Column(db.Integer, db.ForeignKey("cars.id_car"))
    quantity = db.Column(db.Float, default=1.0, nullable=False)
    price = db.Column(db.Float)
    amount = db.Column(db.Float)

    ho = db.relationship("HOInstance", back_populates="positions")
    car = db.relationship("Car")

    def to_dict(self):
        return {
            "id_position": self.id_position,
            "id_ho": self.id_ho,
            "id_car": self.id_car,
            "car_name": self.car.short_name if self.car else None,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
        }

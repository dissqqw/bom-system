from ..database import db


class ProfessionClassifier(db.Model):
    """Справочник профессий.

    hourly_rate — стоимость одного часа труда по профессии. Это поле
    добавлено для выполнения требования о калькуляции стоимости труда.
    """

    __tablename__ = "tm_profession_classifiers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    hourly_rate = db.Column(db.Numeric(12, 2), nullable=True)

    route_positions = db.relationship(
        "RoutePosition",
        back_populates="profession",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "hourly_rate": (
                str(self.hourly_rate)
                if self.hourly_rate is not None else None
            ),
        }

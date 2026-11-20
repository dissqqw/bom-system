from ..database import db


class WorkCenter(db.Model):
    """Групповой рабочий центр (участок или группа оборудования)."""

    __tablename__ = "tm_work_centers"

    id_grc = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    hourly_rate = db.Column(db.Numeric(12, 2), nullable=True)

    route_positions = db.relationship(
        "RoutePosition",
        back_populates="work_center",
    )

    def to_dict(self):
        return {
            "id_grc": self.id_grc,
            "name": self.name,
            "hourly_rate": (
                str(self.hourly_rate)
                if self.hourly_rate is not None else None
            ),
        }



from ..database import db


class ProductClassifier(db.Model):
    __tablename__ = 'product_classifiers'

    id_classifier = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('product_classifiers.id_classifier'),
        nullable=True
    )

    parent = db.relationship(
        'ProductClassifier',
        backref=db.backref('children', lazy='select'),
        remote_side=[id_classifier]
    )

    def to_dict(self):
        return {
            'id_classifier': self.id_classifier,
            'name': self.name,
            'parent_id': self.parent_id
        }

    def check_cycle(self, new_parent_id):

        if new_parent_id is None:
            return False

        if new_parent_id == self.id_classifier:
            return True

        current = db.session.get(ProductClassifier, new_parent_id)

        while current is not None:
            if current.id_classifier == self.id_classifier:
                return True

            current = current.parent

        return False

    def get_all_children(self):

        result = []

        for child in self.children:
            result.append(child)
            result.extend(child.get_all_children())

        return result

    def get_all_parents(self):

        result = []
        current = self.parent

        while current is not None:
            result.append(current)
            current = current.parent

        return result

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication and profile"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_points = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    last_classification_date = db.Column(db.Date, nullable=True)

    # Relationships
    classifications = db.relationship('Classification', backref='user', lazy='dynamic')
    badges = db.relationship('UserBadge', backref='user', lazy='dynamic')

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    def add_points(self, points):
        """Add points to user's total"""
        self.total_points += points

    def update_streak(self):
        """Update the user's daily streak"""
        today = date.today()

        if self.last_classification_date is None:
            # First classification ever
            self.current_streak = 1
        elif self.last_classification_date == today:
            # Already classified today, no change
            pass
        elif (today - self.last_classification_date).days == 1:
            # Consecutive day, increment streak
            self.current_streak += 1
        else:
            # Streak broken, reset to 1
            self.current_streak = 1

        self.last_classification_date = today

    def get_classification_count(self, category=None):
        """Get total classification count, optionally filtered by category"""
        query = self.classifications
        if category:
            query = query.filter_by(category=category)
        return query.count()

    def get_category_stats(self):
        """Get classification counts by category"""
        from sqlalchemy import func
        stats = db.session.query(
            Classification.category,
            func.count(Classification.id).label('count')
        ).filter(
            Classification.user_id == self.id
        ).group_by(Classification.category).all()

        return {stat.category: stat.count for stat in stats}

    def has_badge(self, badge_id):
        """Check if user has a specific badge"""
        return self.badges.filter_by(badge_id=badge_id).first() is not None

    def __repr__(self):
        return f'<User {self.username}>'


class Classification(db.Model):
    """Record of each classification made by a user"""
    __tablename__ = 'classifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)  # coarse category
    fine_category = db.Column(db.String(50), nullable=True)  # fine-grained category
    confidence = db.Column(db.Float, nullable=True)
    points_earned = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<Classification {self.category} by User {self.user_id}>'


class Badge(db.Model):
    """Badge/Achievement definitions"""
    __tablename__ = 'badges'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=False)  # emoji or icon class
    requirement_type = db.Column(db.String(50), nullable=False)
    # Types: 'total_count', 'category_count', 'streak', 'points'
    requirement_value = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=True)  # for category-specific badges

    # Relationship
    users = db.relationship('UserBadge', backref='badge', lazy='dynamic')

    def check_earned(self, user):
        """Check if a user has earned this badge"""
        if self.requirement_type == 'total_count':
            return user.get_classification_count() >= self.requirement_value

        elif self.requirement_type == 'category_count':
            return user.get_classification_count(self.category) >= self.requirement_value

        elif self.requirement_type == 'streak':
            return user.current_streak >= self.requirement_value

        elif self.requirement_type == 'points':
            return user.total_points >= self.requirement_value

        return False

    def __repr__(self):
        return f'<Badge {self.name}>'


class UserBadge(db.Model):
    """Junction table for user-badge relationship"""
    __tablename__ = 'user_badges'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), nullable=False, index=True)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensure a user can't earn the same badge twice
    __table_args__ = (
        db.UniqueConstraint('user_id', 'badge_id', name='unique_user_badge'),
    )

    def __repr__(self):
        return f'<UserBadge User:{self.user_id} Badge:{self.badge_id}>'

from flask import Flask
from config import Config
from models import db, Badge


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def seed_badges():
    badges = [
        {'name': 'First Sort', 'description': 'Complete your first classification', 'icon': '🌱', 'requirement_type': 'total_count', 'requirement_value': 1, 'category': None},
        {'name': 'Eco Starter', 'description': 'Complete 10 classifications', 'icon': '🌿', 'requirement_type': 'total_count', 'requirement_value': 10, 'category': None},
        {'name': 'Sorting Enthusiast', 'description': 'Complete 50 classifications', 'icon': '🌲', 'requirement_type': 'total_count', 'requirement_value': 50, 'category': None},
        {'name': 'Recycling Pro', 'description': 'Complete 100 classifications', 'icon': '🌳', 'requirement_type': 'total_count', 'requirement_value': 100, 'category': None},
        {'name': 'Eco Master', 'description': 'Complete 500 classifications', 'icon': '🏔️', 'requirement_type': 'total_count', 'requirement_value': 500, 'category': None},
        {'name': 'Plastic Warrior', 'description': 'Sort 50 plastic items', 'icon': '♻️', 'requirement_type': 'category_count', 'requirement_value': 50, 'category': 'plastic'},
        {'name': 'Paper Champion', 'description': 'Sort 50 paper items', 'icon': '📄', 'requirement_type': 'category_count', 'requirement_value': 50, 'category': 'paper'},
        {'name': 'Cardboard Crusher', 'description': 'Sort 50 cardboard items', 'icon': '📦', 'requirement_type': 'category_count', 'requirement_value': 50, 'category': 'cardboard'},
        {'name': 'Metal Master', 'description': 'Sort 50 metal items', 'icon': '🔧', 'requirement_type': 'category_count', 'requirement_value': 50, 'category': 'metal'},
        {'name': 'Week Warrior', 'description': 'Maintain a 7-day sorting streak', 'icon': '🔥', 'requirement_type': 'streak', 'requirement_value': 7, 'category': None},
        {'name': 'Month Master', 'description': 'Maintain a 30-day sorting streak', 'icon': '⭐', 'requirement_type': 'streak', 'requirement_value': 30, 'category': None},
        {'name': 'Century Club', 'description': 'Earn 1,000 total points', 'icon': '💯', 'requirement_type': 'points', 'requirement_value': 1000, 'category': None},
        {'name': 'Point Collector', 'description': 'Earn 5,000 total points', 'icon': '🎯', 'requirement_type': 'points', 'requirement_value': 5000, 'category': None},
        {'name': 'Eco Legend', 'description': 'Earn 10,000 total points', 'icon': '🏆', 'requirement_type': 'points', 'requirement_value': 10000, 'category': None},
    ]

    for badge_data in badges:
        existing = Badge.query.filter_by(name=badge_data['name']).first()
        if not existing:
            badge = Badge(**badge_data)
            db.session.add(badge)
            print(f"Added badge: {badge_data['icon']} {badge_data['name']}")
        else:
            print(f"Badge exists: {badge_data['name']}")

    db.session.commit()
    print("\nDone seeding badges!")


def init_database():
    app = create_app()

    with app.app_context():
        print("Creating tables...")
        db.create_all()
        print("Tables created!")

        print("\nSeeding badges...")
        seed_badges()

        print(f"\nDatabase ready at: {Config.SQLALCHEMY_DATABASE_URI}")


if __name__ == '__main__':
    init_database()

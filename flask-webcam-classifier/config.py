import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ecosort-secret-key-change-in-production'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'ecosort.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hrs

    # points config
    POINTS_PER_CLASSIFICATION = 10
    POINTS_RECYCLABLE_BONUS = 5
    POINTS_TRASH = 5
    POINTS_STREAK_MULTIPLIER = 2

    # kg CO2 saved per item
    IMPACT_FACTORS = {
        'plastic': 0.5,
        'paper': 0.3,
        'cardboard': 0.4,
        'metal': 1.0,
        'glass': 0.3,
        'trash': 0.0
    }

    # map fine categories to coarse ones
    FINE_TO_COARSE = {
        "E-waste": "metal",
        "Metal-waste": "metal",
        "bottles": "plastic",
        "cardboard": "cardboard",
        "cups": "plastic",
        "organic-waste": "trash",
        "other-trash": "trash",
        "paper": "paper",
        "plastic-waste": "plastic",
        "trash": "trash",
        "trashbin": "trash",
        "metal": "metal",
        "glass": "glass",
        "plastic": "plastic",
    }

    RECYCLABLE_CATEGORIES = ['plastic', 'paper', 'cardboard', 'metal', 'glass']

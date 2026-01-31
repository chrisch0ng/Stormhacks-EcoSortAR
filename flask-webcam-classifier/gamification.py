from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import db, User, Badge, UserBadge, Classification
from config import Config

gamification_bp = Blueprint('gamification', __name__)


def calculate_points(category, streak_days=0):
    base_points = Config.POINTS_PER_CLASSIFICATION

    if category in Config.RECYCLABLE_CATEGORIES:
        base_points += Config.POINTS_RECYCLABLE_BONUS
    elif category == 'trash':
        base_points = Config.POINTS_TRASH

    streak_bonus = streak_days * Config.POINTS_STREAK_MULTIPLIER
    return base_points + streak_bonus


def record_classification(user, category, fine_category=None, confidence=None):
    user.update_streak()
    points = calculate_points(category, user.current_streak)

    classification = Classification(
        user_id=user.id,
        category=category,
        fine_category=fine_category,
        confidence=confidence,
        points_earned=points
    )

    user.add_points(points)
    db.session.add(classification)
    db.session.commit()

    new_badges = check_and_award_badges(user)

    return {
        'points_earned': points,
        'total_points': user.total_points,
        'streak': user.current_streak,
        'new_badges': new_badges
    }


def check_and_award_badges(user):
    new_badges = []
    all_badges = Badge.query.all()

    for badge in all_badges:
        if user.has_badge(badge.id):
            continue

        if badge.check_earned(user):
            user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
            db.session.add(user_badge)
            new_badges.append({
                'id': badge.id,
                'name': badge.name,
                'description': badge.description,
                'icon': badge.icon
            })

    if new_badges:
        db.session.commit()

    return new_badges


def get_leaderboard(limit=10, timeframe='all'):
    from datetime import datetime, timedelta
    from sqlalchemy import func

    if timeframe == 'all':
        users = User.query.order_by(User.total_points.desc()).limit(limit).all()
        return [
            {
                'rank': i + 1,
                'username': user.username,
                'points': user.total_points,
                'streak': user.current_streak,
                'badge_count': user.badges.count()
            }
            for i, user in enumerate(users)
        ]
    else:
        if timeframe == 'weekly':
            start_date = datetime.utcnow() - timedelta(days=7)
        else:
            start_date = datetime.utcnow() - timedelta(days=30)

        results = db.session.query(
            User.id,
            User.username,
            User.current_streak,
            func.coalesce(func.sum(Classification.points_earned), 0).label('period_points')
        ).outerjoin(
            Classification,
            (Classification.user_id == User.id) &
            (Classification.created_at >= start_date)
        ).group_by(User.id).order_by(
            func.coalesce(func.sum(Classification.points_earned), 0).desc()
        ).limit(limit).all()

        return [
            {
                'rank': i + 1,
                'username': result.username,
                'points': int(result.period_points),
                'streak': result.current_streak,
                'badge_count': User.query.get(result.id).badges.count()
            }
            for i, result in enumerate(results)
        ]


def get_user_rank(user):
    higher_count = User.query.filter(User.total_points > user.total_points).count()
    return higher_count + 1


@gamification_bp.route('/api/leaderboard')
@gamification_bp.route('/api/leaderboard/<timeframe>')
def api_leaderboard(timeframe='all'):
    if timeframe not in ['all', 'weekly', 'monthly']:
        timeframe = 'all'

    leaderboard = get_leaderboard(limit=10, timeframe=timeframe)

    user_rank = None
    if current_user.is_authenticated:
        user_rank = get_user_rank(current_user)

    return jsonify({
        'success': True,
        'leaderboard': leaderboard,
        'user_rank': user_rank,
        'timeframe': timeframe
    })


@gamification_bp.route('/api/badges')
def api_all_badges():
    badges = Badge.query.all()
    return jsonify({
        'success': True,
        'badges': [
            {
                'id': b.id,
                'name': b.name,
                'description': b.description,
                'icon': b.icon,
                'requirement_type': b.requirement_type,
                'requirement_value': b.requirement_value,
                'category': b.category
            }
            for b in badges
        ]
    })


@gamification_bp.route('/api/user/badges')
@login_required
def api_user_badges():
    user_badges = current_user.badges.all()
    earned_ids = [ub.badge_id for ub in user_badges]
    all_badges = Badge.query.all()

    return jsonify({
        'success': True,
        'badges': [
            {
                'id': b.id,
                'name': b.name,
                'description': b.description,
                'icon': b.icon,
                'earned': b.id in earned_ids,
                'earned_at': next(
                    (ub.earned_at.isoformat() for ub in user_badges if ub.badge_id == b.id),
                    None
                )
            }
            for b in all_badges
        ],
        'total_earned': len(earned_ids),
        'total_available': len(all_badges)
    })

"""
Gamification system for points, badges, and leaderboard.
"""

from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import db, User, Badge, UserBadge, Classification
from config import Config

gamification_bp = Blueprint('gamification', __name__)


def calculate_points(category, streak_days=0):
    """
    Calculate points earned for a classification.

    Args:
        category: The coarse category of the classified item
        streak_days: Current streak days for bonus calculation

    Returns:
        Total points earned
    """
    base_points = Config.POINTS_PER_CLASSIFICATION

    # Check if it's a recyclable category for bonus
    if category in Config.RECYCLABLE_CATEGORIES:
        base_points += Config.POINTS_RECYCLABLE_BONUS
    elif category == 'trash':
        base_points = Config.POINTS_TRASH

    # Add streak bonus
    streak_bonus = streak_days * Config.POINTS_STREAK_MULTIPLIER

    return base_points + streak_bonus


def record_classification(user, category, fine_category=None, confidence=None):
    """
    Record a classification and award points.

    Args:
        user: User model instance
        category: Coarse category (e.g., 'plastic', 'paper')
        fine_category: Fine-grained category (e.g., 'bottles', 'cups')
        confidence: Classification confidence score

    Returns:
        dict with points earned and any new badges
    """
    # Update streak first (this affects points)
    user.update_streak()

    # Calculate points
    points = calculate_points(category, user.current_streak)

    # Create classification record
    classification = Classification(
        user_id=user.id,
        category=category,
        fine_category=fine_category,
        confidence=confidence,
        points_earned=points
    )

    # Add points to user
    user.add_points(points)

    db.session.add(classification)
    db.session.commit()

    # Check for new badges
    new_badges = check_and_award_badges(user)

    return {
        'points_earned': points,
        'total_points': user.total_points,
        'streak': user.current_streak,
        'new_badges': new_badges
    }


def check_and_award_badges(user):
    """
    Check if user has earned any new badges and award them.

    Args:
        user: User model instance

    Returns:
        List of newly earned badge dicts
    """
    new_badges = []
    all_badges = Badge.query.all()

    for badge in all_badges:
        # Skip if user already has this badge
        if user.has_badge(badge.id):
            continue

        # Check if badge is earned
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
    """
    Get the leaderboard of top users.

    Args:
        limit: Number of users to return
        timeframe: 'all', 'weekly', or 'monthly'

    Returns:
        List of user dicts with rank, username, and points
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func

    if timeframe == 'all':
        # All-time leaderboard based on total_points
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
        # Time-based leaderboard
        if timeframe == 'weekly':
            start_date = datetime.utcnow() - timedelta(days=7)
        else:  # monthly
            start_date = datetime.utcnow() - timedelta(days=30)

        # Sum points from classifications in timeframe
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
    """
    Get the user's rank on the leaderboard.

    Args:
        user: User model instance

    Returns:
        User's rank (1-indexed)
    """
    higher_count = User.query.filter(User.total_points > user.total_points).count()
    return higher_count + 1


# API Routes

@gamification_bp.route('/api/leaderboard')
@gamification_bp.route('/api/leaderboard/<timeframe>')
def api_leaderboard(timeframe='all'):
    """Get leaderboard data"""
    if timeframe not in ['all', 'weekly', 'monthly']:
        timeframe = 'all'

    leaderboard = get_leaderboard(limit=10, timeframe=timeframe)

    # Include current user's rank if logged in
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
    """Get all available badges"""
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
    """Get current user's earned badges"""
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

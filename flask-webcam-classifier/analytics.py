"""
Analytics blueprint for dashboard data and environmental impact calculations.
"""

from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user
from models import db, Classification
from config import Config
from datetime import datetime, timedelta
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)


def calculate_environmental_impact(user):
    """
    Calculate the environmental impact of a user's recycling efforts.

    Args:
        user: User model instance

    Returns:
        dict with various impact metrics
    """
    # Get category counts
    category_counts = db.session.query(
        Classification.category,
        func.count(Classification.id).label('count')
    ).filter(
        Classification.user_id == user.id
    ).group_by(Classification.category).all()

    category_dict = {c.category: c.count for c in category_counts}

    # Calculate CO2 saved (kg)
    co2_saved = 0
    for category, count in category_dict.items():
        impact_factor = Config.IMPACT_FACTORS.get(category, 0)
        co2_saved += count * impact_factor

    # Calculate equivalent metrics
    # Average tree absorbs ~22 kg CO2 per year
    trees_equivalent = co2_saved / 22

    # Average landfill space per item (liters)
    landfill_saved = sum(category_dict.values()) * 0.5  # 0.5L per item average

    # Energy saved (kWh) - rough estimates
    # Recycling aluminum saves ~14 kWh per kg
    # Recycling plastic saves ~5.8 kWh per kg
    # Recycling paper saves ~4.1 kWh per kg
    energy_saved = (
        category_dict.get('Metal', 0) * 2.0 +  # ~2 kWh per item
        category_dict.get('plastic', 0) * 0.5 +
        category_dict.get('paper', 0) * 0.3 +
        category_dict.get('cardboard', 0) * 0.4
    )

    return {
        'co2_saved_kg': round(co2_saved, 2),
        'trees_equivalent': round(trees_equivalent, 2),
        'landfill_saved_liters': round(landfill_saved, 2),
        'energy_saved_kwh': round(energy_saved, 2),
        'total_items_sorted': sum(category_dict.values()),
        'recyclables_sorted': sum(
            count for cat, count in category_dict.items()
            if cat in Config.RECYCLABLE_CATEGORIES
        )
    }


def get_classification_history(user, limit=50):
    """
    Get recent classification history for a user.

    Args:
        user: User model instance
        limit: Maximum number of records to return

    Returns:
        List of classification dicts
    """
    classifications = Classification.query.filter_by(
        user_id=user.id
    ).order_by(
        Classification.created_at.desc()
    ).limit(limit).all()

    return [
        {
            'id': c.id,
            'category': c.category,
            'fine_category': c.fine_category,
            'confidence': round(c.confidence * 100, 1) if c.confidence else None,
            'points_earned': c.points_earned,
            'created_at': c.created_at.isoformat()
        }
        for c in classifications
    ]


def get_weekly_activity(user):
    """
    Get classification activity for the past 7 days.

    Args:
        user: User model instance

    Returns:
        List of daily counts for the past week
    """
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=6)

    # Query daily counts
    daily_counts = db.session.query(
        func.date(Classification.created_at).label('date'),
        func.count(Classification.id).label('count')
    ).filter(
        Classification.user_id == user.id,
        func.date(Classification.created_at) >= week_ago
    ).group_by(
        func.date(Classification.created_at)
    ).all()

    # Convert to dict for easy lookup
    count_dict = {str(d.date): d.count for d in daily_counts}

    # Build complete week with zeros for missing days
    result = []
    for i in range(7):
        date = week_ago + timedelta(days=i)
        date_str = str(date)
        result.append({
            'date': date_str,
            'day': date.strftime('%a'),
            'count': count_dict.get(date_str, 0)
        })

    return result


def get_category_breakdown(user):
    """
    Get classification breakdown by category.

    Args:
        user: User model instance

    Returns:
        List of category counts with percentages
    """
    total = Classification.query.filter_by(user_id=user.id).count()

    if total == 0:
        return []

    category_counts = db.session.query(
        Classification.category,
        func.count(Classification.id).label('count')
    ).filter(
        Classification.user_id == user.id
    ).group_by(Classification.category).all()

    # Define colors for each category
    colors = {
        'plastic': '#FF6384',
        'paper': '#36A2EB',
        'cardboard': '#FFCE56',
        'Metal': '#4BC0C0',
        'glass': '#9966FF',
        'trash': '#808080'
    }

    return [
        {
            'category': c.category,
            'count': c.count,
            'percentage': round((c.count / total) * 100, 1),
            'color': colors.get(c.category, '#999999')
        }
        for c in category_counts
    ]


# API Routes

@analytics_bp.route('/api/stats')
@login_required
def api_stats():
    """Get user statistics"""
    user = current_user

    return jsonify({
        'success': True,
        'stats': {
            'total_points': user.total_points,
            'current_streak': user.current_streak,
            'total_classifications': user.get_classification_count(),
            'badges_earned': user.badges.count(),
            'member_since': user.created_at.isoformat()
        }
    })


@analytics_bp.route('/api/history')
@login_required
def api_history():
    """Get classification history"""
    limit = min(int(request.args.get('limit', 50)), 100)
    history = get_classification_history(current_user, limit)

    return jsonify({
        'success': True,
        'history': history
    })


@analytics_bp.route('/api/impact')
@login_required
def api_impact():
    """Get environmental impact data"""
    impact = calculate_environmental_impact(current_user)

    return jsonify({
        'success': True,
        'impact': impact
    })


@analytics_bp.route('/api/weekly-activity')
@login_required
def api_weekly_activity():
    """Get weekly activity data for charts"""
    activity = get_weekly_activity(current_user)

    return jsonify({
        'success': True,
        'activity': activity
    })


@analytics_bp.route('/api/category-breakdown')
@login_required
def api_category_breakdown():
    """Get category breakdown for pie chart"""
    breakdown = get_category_breakdown(current_user)

    return jsonify({
        'success': True,
        'breakdown': breakdown
    })


# Page Routes

@analytics_bp.route('/dashboard')
@login_required
def dashboard():
    """Render the analytics dashboard"""
    stats = {
        'total_points': current_user.total_points,
        'current_streak': current_user.current_streak,
        'total_classifications': current_user.get_classification_count(),
        'badges_earned': current_user.badges.count()
    }
    impact = calculate_environmental_impact(current_user)

    return render_template('dashboard.html', stats=stats, impact=impact)


# Need to import request for the history endpoint
from flask import request

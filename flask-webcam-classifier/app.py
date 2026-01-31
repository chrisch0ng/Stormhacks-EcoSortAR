from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from config import Config
from models import db, User

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Register blueprints
from auth import auth_bp
from gamification import gamification_bp
from analytics import analytics_bp

app.register_blueprint(auth_bp)
app.register_blueprint(gamification_bp)
app.register_blueprint(analytics_bp)

# Check if Roboflow is configured
from roboflow_detect import is_roboflow_configured, detect_waste_roboflow
USE_ROBOFLOW = is_roboflow_configured()

if USE_ROBOFLOW:
    print("Using Roboflow API for classification")
else:
    print("Roboflow not configured, falling back to local YOLO model")
    # Only load local model if Roboflow not available
    import numpy as np
    import cv2
    import base64
    from io import BytesIO
    from PIL import Image
    from ultralytics import YOLO

    model = YOLO('my_model.pt')
    with open('labels.txt', 'r') as f:
        coarse_labels = [line.strip() for line in f.readlines()]


@app.route('/')
@login_required
def index():
    """Render the main classifier page"""
    return render_template('index.html')


@app.route('/leaderboard')
def leaderboard():
    """Render the leaderboard page"""
    return render_template('leaderboard.html')


@app.route('/profile')
@login_required
def profile():
    """Render the user profile page"""
    from gamification import get_user_rank

    user = current_user
    rank = get_user_rank(user)
    total_classifications = user.get_classification_count()
    category_stats = user.get_category_stats()

    return render_template('profile.html',
                           user=user,
                           rank=rank,
                           total_classifications=total_classifications,
                           category_stats=category_stats)


@app.route('/classify', methods=['POST'])
@login_required
def classify():
    """Classify image from webcam and record for gamification"""
    from gamification import record_classification

    try:
        data = request.get_json()
        image_data = data['image']

        if USE_ROBOFLOW:
            # Use Roboflow API
            result = detect_waste_roboflow(image_data)

            if not result['success']:
                return jsonify(result), 500

            predictions = result['predictions']
            boxes = result['boxes']

        else:
            # Use local YOLO model (fallback)
            import numpy as np
            import cv2
            import base64
            from io import BytesIO
            from PIL import Image

            # Remove the data URL prefix
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes)).convert('RGB')

            # Convert to numpy array
            image_rgb = np.array(image)
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            image_bgr = cv2.resize(image_rgb, (640, 480))

            # Run inference with YOLO model
            results = model(image_bgr, verbose=False)
            result = results[0]

            class_names = model.names
            coarse_predictions = np.zeros(len(coarse_labels))
            detections = result.boxes

            if len(detections) > 0:
                for i in range(len(detections)):
                    class_idx = int(detections[i].cls.item())
                    fine_class_name = class_names[class_idx]
                    confidence = detections[i].conf.item()

                    if fine_class_name in coarse_labels:
                        coarse_idx = coarse_labels.index(fine_class_name)
                        coarse_predictions[coarse_idx] += confidence

            predictions = []
            for i, label in enumerate(coarse_labels):
                predictions.append({
                    'label': label,
                    'confidence': float(coarse_predictions[i])
                })
            predictions = sorted(predictions, key=lambda x: x['confidence'], reverse=True)

            boxes = []
            if len(result.boxes) > 0:
                for box in result.boxes:
                    class_idx = int(box.cls.cpu().numpy())
                    confidence = float(box.conf.cpu().numpy())
                    fine_class_name = class_names[class_idx]
                    coarse_category = Config.FINE_TO_COARSE.get(fine_class_name, fine_class_name)

                    if fine_class_name in coarse_labels:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        boxes.append({
                            'x1': float(x1),
                            'y1': float(y1),
                            'x2': float(x2),
                            'y2': float(y2),
                            'confidence': confidence,
                            'class': coarse_category,
                            'fine_class': fine_class_name
                        })

        # Handle gamification for top detection
        gamification_results = None
        if boxes:
            # Find highest confidence detection
            top_box = max(boxes, key=lambda x: x['confidence'])

            # Record if confidence > 0.3 (lowered threshold for Roboflow)
            if top_box['confidence'] > 0.3:
                gamification_results = record_classification(
                    user=current_user,
                    category=top_box['class'],
                    fine_category=top_box.get('fine_class', top_box['class']),
                    confidence=top_box['confidence']
                )

        response_data = {
            'success': True,
            'predictions': predictions,
            'boxes': boxes,
            'model': 'roboflow' if USE_ROBOFLOW else 'local'
        }

        if gamification_results:
            response_data['gamification'] = gamification_results

        return jsonify(response_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Create database tables on first request
@app.before_request
def create_tables():
    if not hasattr(app, '_got_first_request_done'):
        db.create_all()
        app._got_first_request_done = True


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)

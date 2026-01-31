"""
Roboflow API integration for waste detection.
Uses Roboflow's hosted models for better accuracy.
"""

import os
import base64
from inference_sdk import InferenceHTTPClient

# Initialize Roboflow client
ROBOFLOW_API_KEY = os.environ.get('ROBOFLOW_API_KEY', '')

# Model options - you can change these to use different models
# Popular waste detection models on Roboflow Universe:
# - "garbage-classification-3/2" - 6 classes: cardboard, glass, metal, paper, plastic, trash
# - "waste-detection-zaofp/1" - Multiple waste types
# - "taco-trash-annotations-in-context/11" - TACO dataset model

MODEL_ID = os.environ.get('ROBOFLOW_MODEL_ID', 'garbage-classification-3/2')

# Mapping from Roboflow model classes to our app's categories
ROBOFLOW_TO_APP_MAPPING = {
    # Common mappings for waste classification models
    'cardboard': 'cardboard',
    'glass': 'glass',
    'metal': 'Metal',
    'paper': 'paper',
    'plastic': 'plastic',
    'trash': 'trash',
    'organic': 'trash',
    'battery': 'Metal',
    'biological': 'trash',
    'clothes': 'trash',
    'shoes': 'trash',
    'white-glass': 'glass',
    'brown-glass': 'glass',
    'green-glass': 'glass',
    # Add more mappings as needed based on the model you use
}


def get_roboflow_client():
    """Get or create Roboflow inference client."""
    if not ROBOFLOW_API_KEY:
        raise ValueError("ROBOFLOW_API_KEY environment variable not set")

    return InferenceHTTPClient(
        api_url="https://detect.roboflow.com",
        api_key=ROBOFLOW_API_KEY
    )


def detect_waste_roboflow(image_base64):
    """
    Detect waste in an image using Roboflow API.

    Args:
        image_base64: Base64 encoded image string (with or without data URL prefix)

    Returns:
        dict with predictions and boxes
    """
    try:
        client = get_roboflow_client()

        # Remove data URL prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]

        # Run inference
        result = client.infer(image_base64, model_id=MODEL_ID)

        # Process predictions
        predictions = {}
        boxes = []

        if 'predictions' in result:
            for pred in result['predictions']:
                class_name = pred.get('class', 'unknown')
                confidence = pred.get('confidence', 0)

                # Map to our app's categories
                app_category = ROBOFLOW_TO_APP_MAPPING.get(
                    class_name.lower(),
                    class_name
                )

                # Aggregate confidence by category
                if app_category in predictions:
                    predictions[app_category] = max(predictions[app_category], confidence)
                else:
                    predictions[app_category] = confidence

                # Extract bounding box
                x = pred.get('x', 0)
                y = pred.get('y', 0)
                width = pred.get('width', 0)
                height = pred.get('height', 0)

                boxes.append({
                    'x1': x - width / 2,
                    'y1': y - height / 2,
                    'x2': x + width / 2,
                    'y2': y + height / 2,
                    'confidence': confidence,
                    'class': app_category,
                    'fine_class': class_name
                })

        # Convert predictions dict to sorted list
        prediction_list = [
            {'label': k, 'confidence': v}
            for k, v in predictions.items()
        ]
        prediction_list.sort(key=lambda x: x['confidence'], reverse=True)

        # If no predictions, add zero-confidence defaults
        if not prediction_list:
            default_categories = ['plastic', 'paper', 'cardboard', 'Metal', 'glass', 'trash']
            prediction_list = [{'label': cat, 'confidence': 0.0} for cat in default_categories]

        return {
            'success': True,
            'predictions': prediction_list,
            'boxes': boxes,
            'model_used': MODEL_ID
        }

    except ValueError as e:
        return {
            'success': False,
            'error': str(e),
            'predictions': [],
            'boxes': []
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Roboflow API error: {str(e)}",
            'predictions': [],
            'boxes': []
        }


def is_roboflow_configured():
    """Check if Roboflow API is properly configured."""
    return bool(ROBOFLOW_API_KEY)

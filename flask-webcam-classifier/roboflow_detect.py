import os
from inference_sdk import InferenceHTTPClient

ROBOFLOW_API_KEY = os.environ.get('ROBOFLOW_API_KEY', '')
MODEL_ID = os.environ.get('ROBOFLOW_MODEL_ID', 'garbage-classification-3/2')

# map roboflow classes to our categories
ROBOFLOW_TO_APP_MAPPING = {
    'cardboard': 'cardboard',
    'glass': 'glass',
    'metal': 'metal',
    'paper': 'paper',
    'plastic': 'plastic',
    'trash': 'trash',
    'organic': 'trash',
    'battery': 'metal',
    'biological': 'trash',
    'clothes': 'trash',
    'shoes': 'trash',
    'white-glass': 'glass',
    'brown-glass': 'glass',
    'green-glass': 'glass',
}


def get_roboflow_client():
    if not ROBOFLOW_API_KEY:
        raise ValueError("ROBOFLOW_API_KEY not set")

    return InferenceHTTPClient(
        api_url="https://detect.roboflow.com",
        api_key=ROBOFLOW_API_KEY
    )


def detect_waste_roboflow(image_base64):
    try:
        client = get_roboflow_client()

        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]

        result = client.infer(image_base64, model_id=MODEL_ID)

        predictions = {}
        boxes = []

        if 'predictions' in result:
            for pred in result['predictions']:
                class_name = pred.get('class', 'unknown')
                confidence = pred.get('confidence', 0)

                app_category = ROBOFLOW_TO_APP_MAPPING.get(
                    class_name.lower(),
                    class_name
                )

                if app_category in predictions:
                    predictions[app_category] = max(predictions[app_category], confidence)
                else:
                    predictions[app_category] = confidence

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

        prediction_list = [
            {'label': k, 'confidence': v}
            for k, v in predictions.items()
        ]
        prediction_list.sort(key=lambda x: x['confidence'], reverse=True)

        if not prediction_list:
            default_categories = ['plastic', 'paper', 'cardboard', 'metal', 'glass', 'trash']
            prediction_list = [{'label': cat, 'confidence': 0.0} for cat in default_categories]

        return {
            'success': True,
            'predictions': prediction_list,
            'boxes': boxes,
            'model_used': MODEL_ID
        }

    except ValueError as e:
        return {'success': False, 'error': str(e), 'predictions': [], 'boxes': []}
    except Exception as e:
        return {'success': False, 'error': f"Roboflow API error: {str(e)}", 'predictions': [], 'boxes': []}


def is_roboflow_configured():
    return bool(ROBOFLOW_API_KEY)

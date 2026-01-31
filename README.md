# EcoSort

EcoSort is a waste-sorting app that leverages augmented reality to show what type of waste bin your waste belongs to, and incentivizes users to learn proper sorting habits over time. 


EcoSort tackles the issue of recycling contamination, a major problem in North America where only about 25–27% of recyclable waste is properly diverted, resulting in billions of dollars in unnecessary costs—over $20 million in extra expenses for Toronto alone and more than $3.5 billion across the U.S. due to manual sorting, lost material value, and landfilling rejected loads.

## Demo

![Classifying paper waste](images/eco.png)

![Classifying plastic waste](images/eco2.png)

## Features

- **Real-time Classification**: Continuous webcam analysis with bounding box overlays
- **ML-Powered**: Roboflow API integration with fallback to local YOLO model
- **Gamification System**:
  - Points for each classification (bonus for recyclables)
  - Daily streaks with multipliers
  - 14 unlockable badges
  - Global leaderboard
- **User Accounts**: Registration, login, profile pages
- **Analytics Dashboard**: Track your environmental impact with charts
- **Voice Feedback**: Optional audio announcements for classifications
- **Classification Categories**:
  - Cardboard
  - Glass
  - Metal
  - Paper
  - Plastic
  - Trash

## Prerequisites

- Python 3.8 or higher
- Webcam
- Modern web browser (Chrome, Firefox, Edge, Safari)


## Technologies Used

- **Backend**: Flask, Flask-Login, Flask-SQLAlchemy
- **Database**: SQLite
- **ML/Classification**: Roboflow API, YOLOv8 (fallback)
- **Image Processing**: OpenCV, Pillow, NumPy
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js
- **Webcam API**: MediaDevices Web API
- **Voice**: Web Speech API


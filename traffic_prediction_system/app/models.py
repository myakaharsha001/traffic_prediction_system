from datetime import datetime
from flask_login import UserMixin
from . import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TrafficRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(160), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    vehicle_count = db.Column(db.Integer, nullable=False)
    average_speed = db.Column(db.Float, nullable=False)
    time_of_day = db.Column(db.String(30), nullable=False)
    weather = db.Column(db.String(40), nullable=False)
    incident = db.Column(db.String(60), nullable=False)
    road_condition = db.Column(db.String(40), nullable=False)
    visibility = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    traffic_record_id = db.Column(db.Integer, db.ForeignKey("traffic_record.id"), nullable=False)
    low_probability = db.Column(db.Float, nullable=False)
    moderate_probability = db.Column(db.Float, nullable=False)
    high_probability = db.Column(db.Float, nullable=False)
    severe_probability = db.Column(db.Float, nullable=False)
    predicted_condition = db.Column(db.String(30), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="predictions")
    traffic_record = db.relationship("TrafficRecord", backref="prediction", uselist=False)

class Location(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    label=db.Column(db.String(200),nullable=False)
    latitude=db.Column(db.Float,nullable=False)
    longitude=db.Column(db.Float,nullable=False)
    address=db.Column(db.String(500))
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)

class WeatherData(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    latitude=db.Column(db.Float,nullable=False)
    longitude=db.Column(db.Float,nullable=False)
    temperature=db.Column(db.Float)
    humidity=db.Column(db.Float)
    wind_speed=db.Column(db.Float)
    visibility=db.Column(db.Float)
    weather_code=db.Column(db.Integer)
    condition=db.Column(db.String(50))
    retrieved_at=db.Column(db.DateTime,default=datetime.utcnow)

class Incident(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(160),nullable=False)
    incident_type=db.Column(db.String(60),nullable=False)
    description=db.Column(db.Text,nullable=True)
    latitude=db.Column(db.Float,nullable=False)
    longitude=db.Column(db.Float,nullable=False)
    severity=db.Column(db.String(30),nullable=False,default="Medium")
    active=db.Column(db.Boolean,default=True,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    created_by=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)

class PredictionFeedback(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    prediction_id=db.Column(db.Integer,db.ForeignKey("prediction.id"),nullable=False,unique=True)
    actual_condition=db.Column(db.String(30),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    prediction=db.relationship("Prediction",backref=db.backref("feedback",uselist=False))

class Notification(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    prediction_id=db.Column(db.Integer,db.ForeignKey("prediction.id"),nullable=True)
    title=db.Column(db.String(160),nullable=False)
    message=db.Column(db.Text,nullable=False)
    severity=db.Column(db.String(30),nullable=False,default="warning")
    read=db.Column(db.Boolean,default=False,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user=db.relationship("User",backref="notifications")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

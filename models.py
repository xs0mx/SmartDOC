from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_doctor = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100))
    
    # Relationships
    patient_appointments = db.relationship(
        'Appointment',
        foreign_keys='Appointment.patient_id',
        backref='patient',
        lazy=True
    )
    doctor_appointments = db.relationship(
        'Appointment',
        foreign_keys='Appointment.doctor_id',
        backref='doctor',
        lazy=True
    )
    sent_messages = db.relationship(
        'Message',
        foreign_keys='Message.sender_id',
        backref='sender',
        lazy=True
    )
    received_messages = db.relationship(
        'Message',
        foreign_keys='Message.receiver_id',
        backref='receiver',
        lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='scheduled')
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    patient = db.relationship('User', foreign_keys=[patient_id])
    doctor = db.relationship('User', foreign_keys=[doctor_id])

class PatientDiagnosis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    treatment = db.Column(db.Text)
    medications = db.Column(db.Text)
    
    patient = db.relationship('User', backref='diagnoses')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='chat_history')
class UrgentNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    priority_rating = db.Column(db.Integer, nullable=False)
    reasoning = db.Column(db.Text, nullable=False)
    recommended_action = db.Column(db.Text, nullable=False)
    timeframe = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationship to patient
    patient = db.relationship('User', backref='urgent_notifications')
    
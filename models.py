from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Batch(db.Model):
    __tablename__ = 'batch'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    fee_amount = db.Column(db.Float, default=3000.0)
    students = db.relationship('Student', backref='batch_ref', lazy=True)

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    fee_status = db.Column(db.String(20), default='Pending')  # Paid / Pending
    fee_due_date = db.Column(db.Date, nullable=True)
    date_joined = db.Column(db.Date, default=datetime.utcnow)
    attendance_records = db.relationship('Attendance', backref='student_ref', lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    present = db.Column(db.Boolean, default=False)

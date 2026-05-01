"""
Run this ONCE after deploying to populate demo data.
Usage: python seed.py
"""
from app import app, db
from models import Batch, Student, Attendance
from datetime import date, timedelta
import random

NAMES = [
    "Arjun Sharma","Priya Mehta","Rohit Verma","Ananya Singh","Karan Gupta",
    "Neha Joshi","Vikram Yadav","Pooja Nair","Aditya Kumar","Riya Patel",
    "Harsh Malhotra","Swati Chopra","Deepak Rawat","Kavya Reddy","Sahil Bansal",
    "Tanvi Kapoor","Manish Tiwari","Shreya Agarwal","Nikhil Chauhan","Aarav Mishra"
]

def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Batches
        b1 = Batch(name="UPSC Foundation", fee_amount=4500)
        b2 = Batch(name="JEE Mains", fee_amount=5500)
        b3 = Batch(name="NEET Dropper", fee_amount=6000)
        db.session.add_all([b1, b2, b3])
        db.session.commit()

        batches = [b1, b2, b3]
        students = []

        for i, name in enumerate(NAMES):
            batch = batches[i % 3]
            status = random.choice(['Paid', 'Paid', 'Pending'])  # 2/3 paid
            due = date.today() - timedelta(days=random.randint(-5, 20))
            s = Student(
                name=name,
                phone=f"9{random.randint(100000000, 999999999)}",
                batch_id=batch.id,
                fee_status=status,
                fee_due_date=due,
                date_joined=date.today() - timedelta(days=random.randint(10, 90))
            )
            db.session.add(s)
            students.append(s)

        db.session.commit()

        # Attendance — last 14 days
        today = date.today()
        for s in students:
            for d in range(14):
                day = today - timedelta(days=d)
                if day.weekday() < 6:  # Mon–Sat
                    present = random.random() > 0.25  # 75% attendance
                    db.session.add(Attendance(student_id=s.id, date=day, present=present))

        db.session.commit()
        print(f"✅ Seeded: {len(students)} students, 3 batches, attendance for 14 days.")

if __name__ == '__main__':
    seed()

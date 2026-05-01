from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from models import db, Batch, Student, Attendance
from datetime import datetime, date, timedelta
import csv, io, os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'coachOS-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///coachOS.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

ADMIN_EMAIL = 'admin@coachOS.com'
ADMIN_PASSWORD = 'demo123'

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'logged_in' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['email'] == ADMIN_EMAIL and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Try admin@coachOS.com / demo123', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── DASHBOARD ───────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    total_students = Student.query.count()
    total_batches = Batch.query.count()

    first_of_month = date.today().replace(day=1)
    fees_collected = db.session.query(db.func.sum(Batch.fee_amount))\
        .join(Student, Student.batch_id == Batch.id)\
        .filter(Student.fee_status == 'Paid').scalar() or 0

    # Attendance rate this week
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_records = Attendance.query.filter(Attendance.date >= week_start).all()
    att_rate = 0
    if week_records:
        att_rate = round(sum(1 for r in week_records if r.present) / len(week_records) * 100)

    # Batch-wise student count for bar chart
    batches = Batch.query.all()
    batch_labels = [b.name for b in batches]
    batch_counts = [len(b.students) for b in batches]

    # Daily attendance last 14 days for line chart
    days_14 = [(date.today() - timedelta(days=i)) for i in range(13, -1, -1)]
    daily_labels = [d.strftime('%d %b') for d in days_14]
    daily_counts = []
    for d in days_14:
        present = Attendance.query.filter_by(date=d, present=True).count()
        daily_counts.append(present)

    return render_template('dashboard.html',
        total_students=total_students,
        total_batches=total_batches,
        fees_collected=f"{fees_collected:,.0f}",
        att_rate=att_rate,
        batch_labels=batch_labels,
        batch_counts=batch_counts,
        daily_labels=daily_labels,
        daily_counts=daily_counts
    )

# ─── STUDENTS ────────────────────────────────────────────
@app.route('/students')
@login_required
def students():
    all_students = db.session.query(Student, Batch)\
        .join(Batch, Student.batch_id == Batch.id).all()
    batches = Batch.query.all()
    return render_template('students.html', students=all_students, batches=batches)

@app.route('/students/add', methods=['POST'])
@login_required
def add_student():
    name = request.form['name']
    phone = request.form['phone']
    batch_id = int(request.form['batch_id'])
    fee_status = request.form['fee_status']
    due = request.form.get('fee_due_date')
    fee_due = datetime.strptime(due, '%Y-%m-%d').date() if due else None
    s = Student(name=name, phone=phone, batch_id=batch_id,
                fee_status=fee_status, fee_due_date=fee_due,
                date_joined=date.today())
    db.session.add(s)
    db.session.commit()
    flash(f'{name} added successfully.', 'success')
    return redirect(url_for('students'))

@app.route('/students/mark_paid/<int:student_id>', methods=['POST'])
@login_required
def mark_paid(student_id):
    s = Student.query.get_or_404(student_id)
    s.fee_status = 'Paid'
    db.session.commit()
    return jsonify({'status': 'ok', 'name': s.name})

# ─── ATTENDANCE ──────────────────────────────────────────
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    batches = Batch.query.all()
    selected_batch_id = request.args.get('batch_id', type=int)
    selected_date_str = request.args.get('att_date', date.today().isoformat())
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

    students_in_batch = []
    existing = {}
    att_summary = []

    if selected_batch_id:
        students_in_batch = Student.query.filter_by(batch_id=selected_batch_id).all()
        records = Attendance.query.filter(
            Attendance.date == selected_date,
            Attendance.student_id.in_([s.id for s in students_in_batch])
        ).all()
        existing = {r.student_id: r.present for r in records}

        # Attendance % per student last 30 days
        since = date.today() - timedelta(days=30)
        for s in students_in_batch:
            recs = Attendance.query.filter(
                Attendance.student_id == s.id,
                Attendance.date >= since
            ).all()
            pct = round(sum(1 for r in recs if r.present) / len(recs) * 100) if recs else 0
            att_summary.append({'name': s.name, 'pct': pct, 'total': len(recs)})

    if request.method == 'POST':
        batch_id = int(request.form['batch_id'])
        att_date = datetime.strptime(request.form['att_date'], '%Y-%m-%d').date()
        batch_students = Student.query.filter_by(batch_id=batch_id).all()
        present_ids = set(map(int, request.form.getlist('present')))

        for s in batch_students:
            rec = Attendance.query.filter_by(student_id=s.id, date=att_date).first()
            if rec:
                rec.present = s.id in present_ids
            else:
                db.session.add(Attendance(student_id=s.id, date=att_date, present=s.id in present_ids))
        db.session.commit()
        flash('Attendance saved successfully.', 'success')
        return redirect(url_for('attendance', batch_id=batch_id, att_date=att_date.isoformat()))

    return render_template('attendance.html',
        batches=batches,
        students_in_batch=students_in_batch,
        selected_batch_id=selected_batch_id,
        selected_date=selected_date_str,
        existing=existing,
        att_summary=att_summary
    )

# ─── FEES ────────────────────────────────────────────────
@app.route('/fees')
@login_required
def fees():
    today = date.today()
    rows = db.session.query(Student, Batch).join(Batch, Student.batch_id == Batch.id).all()
    fee_data = []
    for s, b in rows:
        days_overdue = 0
        if s.fee_status == 'Pending' and s.fee_due_date:
            delta = (today - s.fee_due_date).days
            days_overdue = max(0, delta)
        fee_data.append({
            'id': s.id,
            'name': s.name,
            'batch': b.name,
            'amount': b.fee_amount,
            'due_date': s.fee_due_date,
            'status': s.fee_status,
            'days_overdue': days_overdue
        })

    collected = sum(r['amount'] for r in fee_data if r['status'] == 'Paid')
    pending = sum(r['amount'] for r in fee_data if r['status'] == 'Pending')

    return render_template('fees.html',
        fee_data=fee_data,
        collected=f"{collected:,.0f}",
        pending=f"{pending:,.0f}"
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

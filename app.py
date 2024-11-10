from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, login_manager
from models import User, ChatMessage, PatientDiagnosis, UrgentNotification
from chat_service import ChatService
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
# Rest of the code remains the same
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize chat service
chat_service = ChatService()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated and current_user.is_doctor:
        return redirect(url_for('doctor_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('doctor_dashboard' if user.is_doctor else 'home'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        is_doctor = request.form.get('is_doctor') == 'on'

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(email=email, name=name, is_doctor=is_doctor)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('doctor_dashboard' if is_doctor else 'home'))

    return render_template('register.html')

@app.route('/doctor')
@login_required
def doctor_dashboard():
    if not current_user.is_doctor:
        flash('Access denied. Doctor privileges required.')
        return redirect(url_for('home'))
    return render_template('doctor_dashboard.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400
            
        # Get response from OpenAI
        response = chat_service.get_chat_response(current_user, message)
        
        # Save chat to database
        chat_message = ChatMessage(
            user_id=current_user.id,
            message=message,
            response=response
        )
        db.session.add(chat_message)
        db.session.commit()
        
        return jsonify({
            'response': response,
            'timestamp': chat_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/add-test-diagnosis')
@login_required
def add_test_diagnosis():
    try:
        diagnosis = PatientDiagnosis(
            patient_id=current_user.id,
            diagnosis="Type 2 Diabetes",
            treatment="Diet modification and regular exercise",
            medications="Metformin 500mg twice daily"
        )
        db.session.add(diagnosis)
        db.session.commit()
        return "Test diagnosis added successfully!"
    except Exception as e:
        return f"Error adding diagnosis: {str(e)}"

@app.route('/api/chat-history')
@login_required
def chat_history():
    history = ChatMessage.query.filter_by(user_id=current_user.id)\
        .order_by(ChatMessage.timestamp.desc())\
        .limit(10)\
        .all()
        
    return jsonify([{
        'message': chat.message,
        'response': chat.response,
        'timestamp': chat.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for chat in history])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
@app.route('/api/urgent-notifications')
@login_required
def get_urgent_notifications():
    if not current_user.is_doctor:
        return jsonify({'error': 'Unauthorized'}), 403
        
    notifications = UrgentNotification.query\
        .filter(UrgentNotification.is_read == False)\
        .order_by(UrgentNotification.priority_rating.desc())\
        .all()
        
    return jsonify([{
        'id': n.id,
        'patient_name': n.patient.name,
        'priority_rating': n.priority_rating,
        'reasoning': n.reasoning,
        'recommended_action': n.recommended_action,
        'timeframe': n.timeframe,
        'timestamp': n.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for n in notifications])

@app.route('/api/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    if not current_user.is_doctor:
        return jsonify({'error': 'Unauthorized'}), 403
        
    notification = UrgentNotification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/patient-priorities')
@login_required
def get_patient_priorities():
    if not current_user.is_doctor:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all patients with recent chat activity
    recent_chats = db.session.query(
        ChatMessage.user_id,
        ChatMessage.message,
        ChatMessage.timestamp,
        UrgentNotification.priority_rating,
        UrgentNotification.reasoning,
        UrgentNotification.recommended_action,
        UrgentNotification.timeframe,
        User.name.label('patient_name')
    ).join(
        User, ChatMessage.user_id == User.id
    ).outerjoin(
        UrgentNotification, 
        db.and_(
            UrgentNotification.patient_id == ChatMessage.user_id,
            UrgentNotification.is_read == False
        )
    ).filter(
        User.is_doctor == False
    ).order_by(
        ChatMessage.timestamp.desc()
    ).distinct(
        ChatMessage.user_id
    ).all()

    priorities = []
    for chat in recent_chats:
        priorities.append({
            'patient_id': chat.user_id,
            'patient_name': chat.patient_name,
            'last_message': chat.message,
            'timestamp': chat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'priority_rating': chat.priority_rating if chat.priority_rating else 0,
            'reasoning': chat.reasoning if chat.reasoning else 'No urgent concerns',
            'recommended_action': chat.recommended_action if chat.recommended_action else 'Routine monitoring',
            'timeframe': chat.timeframe if chat.timeframe else 'Non-urgent'
        })

    return jsonify(priorities)
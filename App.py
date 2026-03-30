import os
import random
import re
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_pymongo import PyMongo
from bcrypt import hashpw, gensalt, checkpw
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)

app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/ai_event_planner")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "my-secret-key-12345")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

# Store OTPs
otp_store = {}

# MongoDB Connection
try:
    mongo = PyMongo(app)
    mongo.db.command('ping')
    print("✅ Connected to MongoDB successfully!")
    
    # Create indexes for unique fields
    try:
        existing_indexes = mongo.db.users.index_information()
        
        if "username_1" not in existing_indexes:
            mongo.db.users.create_index("username", unique=True)
            print("✅ Created username index")
        
        if "email_1" not in existing_indexes:
            mongo.db.users.create_index("email", unique=True)
            print("✅ Created email index")
        
        if "phone_1" not in existing_indexes:
            mongo.db.users.create_index("phone", unique=True)
            print("✅ Created phone index")
        else:
            print("✅ Indexes already exist")
            
    except Exception as e:
        print(f"⚠️ Index note: {e}")
        
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")
    print("Make sure MongoDB is running!")
    mongo = None

# ==================== HELPER FUNCTIONS ====================

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def validate_phone(phone):
    """Validate Indian phone number"""
    phone = re.sub(r'[\s\-\(\)]', '', str(phone))
    pattern = r'^(\+91|0)?[6-9]\d{9}$'
    return re.match(pattern, phone) is not None

def format_phone(phone):
    """Format phone to international format"""
    phone = re.sub(r'[\s\-\(\)]', '', str(phone))
    if phone.startswith('0'):
        phone = '+91' + phone[1:]
    elif not phone.startswith('+'):
        phone = '+91' + phone
    return phone

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must have an uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must have a lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must have a number"
    return True, "Strong password"

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username - no spaces, min 3 chars"""
    if " " in username:
        return False, "Username cannot contain spaces"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers and underscore"
    return True, "Valid username"

def get_event_insights(user_id):
    """Get personalized event insights for AI"""
    try:
        events = list(mongo.db.events.find({"user_id": user_id}))
        tasks = list(mongo.db.tasks.find({"user_id": user_id, "completed": False}))
        
        total_events = len(events)
        upcoming_events = len([e for e in events if e["date_time"] > datetime.utcnow()])
        high_priority_tasks = len([t for t in tasks if t.get("priority") == "high"])
        
        return {
            "total_events": total_events,
            "upcoming_events": upcoming_events,
            "pending_tasks": len(tasks),
            "high_priority_tasks": high_priority_tasks
        }
    except:
        return None

def get_ai_response(prompt, user_id=None, username=None):
    """Smart AI response engine"""
    prompt_lower = prompt.lower()
    
    # Get user context if available
    user_context = ""
    if user_id:
        insights = get_event_insights(user_id)
        if insights:
            user_context = f" (User has {insights['total_events']} total events, {insights['upcoming_events']} upcoming, {insights['pending_tasks']} pending tasks with {insights['high_priority_tasks']} high priority)"
    
    # Event Timing & Scheduling
    if any(word in prompt_lower for word in ["best time", "schedule", "timing", "when to", "event time"]):
        return "📅 **Event Timing Tips:**\n• Best times: 10 AM - 4 PM for maximum attendance\n• Avoid Mondays and post-lunch slots (2-3 PM)\n• Weekend events work best for social gatherings\n• Consider your target audience's availability" + user_context
    
    # Venue Selection
    elif any(word in prompt_lower for word in ["venue", "location", "place", "hall", "space"]):
        return "📍 **Venue Selection Guide:**\n• Check capacity (aim for 20% buffer)\n• Visit at same time as your event for actual lighting\n• Ask about parking, accessibility, and backup power\n• Negotiate weekend vs weekday rates\n• Read cancellation policy carefully" + user_context
    
    # Budget Planning
    elif any(word in prompt_lower for word in ["budget", "cost", "money", "spend", "expense", "price"]):
        return "💰 **Budget Allocation (Standard):**\n• Venue: 35-40%\n• Catering: 25-30%\n• Marketing/Invites: 10-15%\n• Entertainment: 10-15%\n• Decor/AV: 5-10%\n• Contingency: 10-15%\n\n💡 Pro tip: Always keep 15% emergency fund!" + user_context
    
    # Catering & Food
    elif any(word in prompt_lower for word in ["food", "catering", "menu", "meal", "dinner", "lunch"]):
        return "🍽️ **Catering Essentials:**\n• Always do a tasting session before booking\n• Plan for dietary restrictions (vegan, gluten-free, allergies)\n• Buffet = social mingling, Plated = formal\n• Estimate: 1.5x food for evening events\n• Ask about setup/cleanup charges" + user_context
    
    # Guest Management
    elif any(word in prompt_lower for word in ["guest", "attendee", "invitation", "rsvp", "people"]):
        return "👥 **Guest Management Tips:**\n• Send save-the-dates 3 months prior\n• Use digital RSVP trackers\n• Expect 20-30% drop in actual attendance\n• Follow up with non-responders 2 weeks before\n• Plan seating arrangements 1 week in advance" + user_context
    
    # Theme & Decor
    elif any(word in prompt_lower for word in ["theme", "decor", "decoration", "design", "style"]):
        return "🎨 **Theme Ideas:**\n• 🌙 Midnight Garden (elegant, moody)\n• 💎 Neo-Minimalist (clean, modern)\n• 🎭 Retro Glam (vintage, bold)\n• 🌿 Eco-Chic (sustainable, natural)\n• 🚀 Futuristic (tech-forward, neon)\n\nMatch colors to your brand/season!" + user_context
    
    # Tasks & Priorities
    elif any(word in prompt_lower for word in ["task", "priority", "to-do", "todo", "pending"]):
        if user_id:
            tasks = list(mongo.db.tasks.find({"user_id": user_id, "completed": False}))
            high_tasks = [t for t in tasks if t.get("priority") == "high"]
            if high_tasks:
                task_list = "\n".join([f"  • {t['text'][:50]}" for t in high_tasks[:5]])
                return f"⚠️ **High Priority Tasks ({len(high_tasks)}):**\n{task_list}\n\nFocus on these first! Need help prioritizing?"
            else:
                return "✅ Great job! No high priority tasks. Keep maintaining this momentum!" + user_context
        return "📋 **Task Management:** Use high/medium/low priorities. Focus on high priority tasks first. Break large tasks into smaller steps!" + user_context
    
    # Event Planning Tips
    elif any(word in prompt_lower for word in ["tip", "advice", "suggestion", "help", "guide"]):
        return "💡 **Quick Event Tips:**\n• Start planning 3-6 months ahead\n• Create a detailed timeline\n• Have backup plans for weather/tech issues\n• Delegate tasks to team members\n• Test all tech before event day\n• Have a point person for emergencies" + user_context
    
    # Marketing & Promotion
    elif any(word in prompt_lower for word in ["promote", "marketing", "advertise", "social media"]):
        return "📢 **Event Promotion Ideas:**\n• Start promotion 4-6 weeks before\n• Use countdown posts on social media\n• Create event hashtag\n• Partner with influencers\n• Early bird discounts\n• Email marketing sequence (3-4 emails)" + user_context
    
    # Speakers & Entertainment
    elif any(word in prompt_lower for word in ["speaker", "entertainment", "performer", "music", "band"]):
        return "🎤 **Entertainment Booking:**\n• Watch full demo videos before booking\n• Get references from past clients\n• Discuss technical requirements early\n• Have backup entertainment\n• Book 3-4 months in advance for popular artists" + user_context
    
    # Vendor Management
    elif any(word in prompt_lower for word in ["vendor", "supplier", "contractor"]):
        return "🤝 **Vendor Management:**\n• Get minimum 3 quotes\n• Check reviews and ask for references\n• Sign detailed contracts with clear deliverables\n• Keep payment schedule (deposit, milestone, final)\n• Build good relationships - it helps in emergencies!" + user_context
    
    # Greetings
    elif any(word in prompt_lower for word in ["hello", "hi", "hey", "namaste", "hola"]):
        greeting = f"👋 Hello{' ' + username if username else ''}! I'm EVE, your AI event planning assistant."
        return greeting + " I can help with timing, venues, budgeting, catering, guest management, themes, tasks, and more. What would you like to know?" + user_context
    
    # Thank you
    elif any(word in prompt_lower for word in ["thank", "thanks", "thx"]):
        return "😊 You're welcome! I'm always here to help with your event planning. Anything else you need assistance with?"
    
    # Events count
    elif any(word in prompt_lower for word in ["how many event", "event count", "my events"]):
        if user_id:
            events = list(mongo.db.events.find({"user_id": user_id}))
            upcoming = [e for e in events if e["date_time"] > datetime.utcnow()]
            return f"📊 You have **{len(events)}** total events. **{len(upcoming)}** are upcoming. Keep planning! 🎉"
        return "You can create events from the Events page. Need help setting one up?"
    
    # Default response
    else:
        return f"🤖 **I'm EVE, your AI Event Planner!**\n\nI can help you with:\n• 📅 Event timing & scheduling\n• 📍 Venue selection tips\n• 💰 Budget planning\n• 🍽️ Catering & menu ideas\n• 👥 Guest management\n• 🎨 Theme & decor inspiration\n• 📋 Task prioritization\n• 🎤 Entertainment booking\n• 📢 Marketing strategies\n\nWhat would you like to know about event planning?{user_context}"

# ==================== ROUTES ====================

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid request data"}), 400
            
            username = data.get("username", "").strip()
            email = data.get("email", "").strip()
            phone = data.get("phone", "").strip()
            password = data.get("password", "")
            
            print("\n" + "="*60)
            print("📝 REGISTRATION ATTEMPT")
            print(f"Username: '{username}'")
            print(f"Email: '{email}'")
            print(f"Phone: '{phone}'")
            print("="*60)
            
            # Validation
            if not username or not email or not phone or not password:
                return jsonify({"error": "All fields are required"}), 400
            
            # Validate username
            is_valid, username_msg = validate_username(username)
            if not is_valid:
                return jsonify({"error": username_msg}), 400
            
            if not validate_email(email):
                return jsonify({"error": "Invalid email format"}), 400
            
            if not validate_phone(phone):
                return jsonify({"error": "Invalid phone number. Enter 10 digit number"}), 400
            
            is_valid, password_msg = validate_password(password)
            if not is_valid:
                return jsonify({"error": password_msg}), 400
            
            formatted_phone = format_phone(phone)
            print(f"Formatted phone: {formatted_phone}")
            
            # Check OTP verification
            if formatted_phone not in otp_store:
                return jsonify({"error": "Please request OTP first"}), 400
            
            stored_otp_data = otp_store[formatted_phone]
            
            if not stored_otp_data.get("verified", False):
                return jsonify({"error": "Please verify your phone with OTP first"}), 400
            
            # Check existing users
            if mongo.db.users.find_one({"username": username}):
                return jsonify({"error": "Username already taken"}), 400
            
            if mongo.db.users.find_one({"email": email}):
                return jsonify({"error": "Email already registered"}), 400
            
            if mongo.db.users.find_one({"phone": formatted_phone}):
                return jsonify({"error": "Phone number already registered"}), 400
            
            # Create user
            hashed_password = hashpw(password.encode('utf-8'), gensalt())
            
            user_document = {
                "username": username,
                "email": email,
                "phone": formatted_phone,
                "password": hashed_password,
                "created_at": datetime.utcnow(),
                "is_active": True
            }
            
            result = mongo.db.users.insert_one(user_document)
            user_id = result.inserted_id
            
            print(f"\n✅✅✅ USER CREATED SUCCESSFULLY! ✅✅✅")
            print(f"   User ID: {user_id}")
            print(f"   Username: {username}")
            print(f"   Phone: {formatted_phone}")
            print("="*60 + "\n")
            
            # Clean up OTP
            if formatted_phone in otp_store:
                del otp_store[formatted_phone]
            
            # Set session
            session["user_id"] = user_id
            session.permanent = True
            
            return jsonify({
                "success": True,
                "redirect": url_for("dashboard"),
                "message": "Account created successfully!"
            }), 200
            
        except Exception as e:
            print(f"\n❌ REGISTRATION ERROR: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Server error: {str(e)}"}), 500
    
    return render_template("register.html")

@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        data = request.get_json()
        phone = data.get("phone", "").strip()
        
        print("\n" + "="*60)
        print("📱 SEND OTP REQUEST")
        print(f"Phone: '{phone}'")
        print("="*60)
        
        if not phone:
            return jsonify({"error": "Phone number required"}), 400
        
        if not validate_phone(phone):
            return jsonify({"error": "Invalid phone number. Enter 10 digit number"}), 400
        
        formatted_phone = format_phone(phone)
        print(f"Formatted phone: {formatted_phone}")
        
        # Check if phone already registered
        if mongo and mongo.db.users.find_one({"phone": formatted_phone}):
            return jsonify({"error": "Phone number already registered"}), 400
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP
        otp_store[formatted_phone] = {
            "otp": otp,
            "expires_at": datetime.utcnow() + timedelta(minutes=5),
            "verified": False
        }
        
        print(f"\n🔑🔑🔑 OTP GENERATED 🔑🔑🔑")
        print(f"   Phone: {formatted_phone}")
        print(f"   OTP: {otp}")
        print(f"   Expires in: 5 minutes")
        print("="*60 + "\n")
        
        return jsonify({
            "success": True,
            "message": f"OTP: {otp}"
        }), 200
        
    except Exception as e:
        print(f"❌ SEND OTP ERROR: {e}")
        return jsonify({"error": "Failed to send OTP"}), 500

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()
        phone = data.get("phone", "").strip()
        otp = data.get("otp", "").strip()
        
        print("\n" + "="*60)
        print("🔐 VERIFY OTP REQUEST")
        print(f"Phone: '{phone}'")
        print(f"OTP Entered: '{otp}'")
        print("="*60)
        
        if not phone or not otp:
            return jsonify({"error": "Phone and OTP required"}), 400
        
        if not validate_phone(phone):
            return jsonify({"error": "Invalid phone number"}), 400
        
        formatted_phone = format_phone(phone)
        print(f"Formatted phone: {formatted_phone}")
        
        if formatted_phone not in otp_store:
            return jsonify({"error": "No OTP found. Request new one."}), 400
        
        stored_data = otp_store[formatted_phone]
        
        # Check expiry
        if datetime.utcnow() > stored_data["expires_at"]:
            del otp_store[formatted_phone]
            return jsonify({"error": "OTP expired. Request new one."}), 400
        
        # Instant verification - NO DELAY
        if stored_data["otp"] == otp:
            otp_store[formatted_phone]["verified"] = True
            print(f"\n✅✅✅ OTP VERIFIED SUCCESSFULLY! ✅✅✅")
            print(f"   Phone: {formatted_phone}")
            print("="*60 + "\n")
            return jsonify({"success": True, "message": "Phone verified!"}), 200
        else:
            print(f"\n❌ OTP MISMATCH!")
            print("="*60 + "\n")
            return jsonify({"error": "Invalid OTP"}), 400
            
    except Exception as e:
        print(f"❌ VERIFY OTP ERROR: {e}")
        return jsonify({"error": "Failed to verify OTP"}), 500

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            
            print("\n" + "="*60)
            print("🔐 LOGIN ATTEMPT")
            print(f"Username/Email/Phone: '{username}'")
            print("="*60)
            
            if not username or not password:
                return render_template("login.html", error="Username and password required")
            
            # Find user by username, email, or phone
            user = None
            
            if "@" in username:
                user = mongo.db.users.find_one({"email": username})
            elif username.startswith('+') or (username.isdigit() and len(username) >= 10):
                formatted_phone = format_phone(username)
                user = mongo.db.users.find_one({"phone": formatted_phone})
            else:
                user = mongo.db.users.find_one({"username": username})
            
            if user and checkpw(password.encode('utf-8'), user["password"]):
                session["user_id"] = user["_id"]
                
                if request.form.get("remember"):
                    session.permanent = True
                
                print(f"\n✅ LOGIN SUCCESSFUL: {user['username']}")
                print("="*60 + "\n")
                return redirect(url_for("dashboard"))
            else:
                print(f"\n❌ LOGIN FAILED: Invalid credentials")
                print("="*60 + "\n")
                return render_template("login.html", error="Invalid credentials")
                
        except Exception as e:
            print(f"❌ LOGIN ERROR: {e}")
            return render_template("login.html", error="Login failed")
    
    success = request.args.get("success")
    return render_template("login.html", success=success)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        try:
            data = request.get_json()
            email = data.get("email", "").strip()
            
            print("\n" + "="*60)
            print("🔐 FORGOT PASSWORD REQUEST")
            print(f"Email: {email}")
            print("="*60)
            
            if not email:
                return jsonify({"error": "Email is required"}), 400
            
            # Check if user exists
            user = mongo.db.users.find_one({"email": email})
            if not user:
                return jsonify({"error": "No account found with this email"}), 400
            
            # Generate OTP
            otp = generate_otp()
            
            # Store OTP for password reset
            otp_store[f"reset_{email}"] = {
                "otp": otp,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "verified": False,
                "email": email
            }
            
            print(f"\n🔑 PASSWORD RESET OTP: {otp}")
            print(f"📧 Email: {email}")
            print("="*60 + "\n")
            
            # Instant response - NO DELAY
            return jsonify({
                "success": True,
                "message": f"OTP sent! Check terminal: {otp}"
            }), 200
            
        except Exception as e:
            print(f"❌ Forgot password error: {e}")
            return jsonify({"error": "Failed to send OTP"}), 500
    
    return render_template("forgot_password.html")

@app.route("/verify-reset-otp", methods=["POST"])
def verify_reset_otp():
    try:
        data = request.get_json()
        email = data.get("email", "").strip()
        otp = data.get("otp", "").strip()
        
        print("\n" + "="*60)
        print("🔐 VERIFY RESET OTP")
        print(f"Email: {email}")
        print(f"OTP: {otp}")
        print("="*60)
        
        if not email or not otp:
            return jsonify({"error": "Email and OTP required"}), 400
        
        key = f"reset_{email}"
        
        if key not in otp_store:
            return jsonify({"error": "No OTP found. Request new one."}), 400
        
        stored_data = otp_store[key]
        
        # Check expiry
        if datetime.utcnow() > stored_data["expires_at"]:
            del otp_store[key]
            return jsonify({"error": "OTP expired. Request new one."}), 400
        
        # Instant verification - NO DELAY
        if stored_data["otp"] == otp:
            otp_store[key]["verified"] = True
            print(f"\n✅ RESET OTP VERIFIED for {email}")
            print("="*60 + "\n")
            return jsonify({"success": True, "message": "OTP verified!"}), 200
        else:
            return jsonify({"error": "Invalid OTP"}), 400
            
    except Exception as e:
        print(f"❌ Verify reset OTP error: {e}")
        return jsonify({"error": "Failed to verify OTP"}), 500

@app.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json()
        email = data.get("email", "").strip()
        new_password = data.get("new_password", "")
        
        print("\n" + "="*60)
        print("🔐 RESET PASSWORD")
        print(f"Email: {email}")
        print("="*60)
        
        if not email or not new_password:
            return jsonify({"error": "Email and new password required"}), 400
        
        # Validate password
        is_valid, password_msg = validate_password(new_password)
        if not is_valid:
            return jsonify({"error": password_msg}), 400
        
        key = f"reset_{email}"
        
        if key not in otp_store or not otp_store[key].get("verified", False):
            return jsonify({"error": "Please verify OTP first"}), 400
        
        # Hash new password
        hashed_password = hashpw(new_password.encode('utf-8'), gensalt())
        
        # Update user password
        result = mongo.db.users.update_one(
            {"email": email},
            {"$set": {"password": hashed_password}}
        )
        
        if result.modified_count > 0:
            # Clean up OTP
            if key in otp_store:
                del otp_store[key]
            
            print(f"\n✅ PASSWORD RESET SUCCESSFUL for {email}")
            print("="*60 + "\n")
            return jsonify({"success": True, "message": "Password reset successful!"}), 200
        else:
            return jsonify({"error": "Failed to reset password"}), 400
            
    except Exception as e:
        print(f"❌ Reset password error: {e}")
        return jsonify({"error": "Failed to reset password"}), 500

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        if not user:
            session.clear()
            return redirect(url_for("login"))
        
        events = list(mongo.db.events.find({"user_id": user["_id"]}).sort("date_time", 1))
        tasks = list(mongo.db.tasks.find({"user_id": user["_id"], "completed": False}))
        
        upcoming = [e for e in events if e["date_time"] > datetime.utcnow()]
        total_attendees = sum(e.get("attendees", 0) for e in events)
        
        return render_template("dashboard.html",
                               user=user,
                               events=events[:3],
                               tasks=tasks[:5],
                               upcoming_count=len(upcoming),
                               total_attendees=total_attendees,
                               total_events=len(events),
                               pending_tasks=len(tasks))
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return redirect(url_for("login"))

@app.route("/events")
def events_list():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        events = list(mongo.db.events.find({"user_id": user["_id"]}).sort("date_time", 1))
        return render_template("events.html", events=events)
    except Exception as e:
        print(f"❌ Events error: {e}")
        return redirect(url_for("dashboard"))

@app.route("/events/create", methods=["POST"])
def create_event():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        data = request.get_json()
        
        try:
            event_date = datetime.fromisoformat(data.get("date_time"))
        except:
            return jsonify({"error": "Invalid datetime"}), 400
        
        new_event = {
            "user_id": user["_id"],
            "title": data.get("title"),
            "date_time": event_date,
            "duration": float(data.get("duration", 1)),
            "attendees": int(data.get("attendees", 0)),
            "created_at": datetime.utcnow()
        }
        
        result = mongo.db.events.insert_one(new_event)
        return jsonify({"id": str(result.inserted_id)}), 201
    except Exception as e:
        print(f"❌ Create event error: {e}")
        return jsonify({"error": "Failed to create event"}), 500

@app.route("/events/delete/<event_id>", methods=["DELETE"])
def delete_event(event_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        mongo.db.events.delete_one({"_id": ObjectId(event_id), "user_id": user["_id"]})
        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        print(f"❌ Delete event error: {e}")
        return jsonify({"error": "Failed to delete"}), 500

@app.route("/tasks")
def tasks_list():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        tasks = list(mongo.db.tasks.find({"user_id": user["_id"]}).sort("priority", -1))
        return render_template("tasks.html", tasks=tasks)
    except Exception as e:
        print(f"❌ Tasks error: {e}")
        return redirect(url_for("dashboard"))

@app.route("/tasks/create", methods=["POST"])
def create_task():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        data = request.get_json()
        
        new_task = {
            "user_id": user["_id"],
            "text": data.get("text"),
            "priority": data.get("priority", "medium"),
            "completed": False,
            "created_at": datetime.utcnow()
        }
        
        result = mongo.db.tasks.insert_one(new_task)
        return jsonify({"id": str(result.inserted_id)}), 201
    except Exception as e:
        print(f"❌ Create task error: {e}")
        return jsonify({"error": "Failed to create task"}), 500

@app.route("/tasks/toggle/<task_id>", methods=["PUT"])
def toggle_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        task = mongo.db.tasks.find_one({"_id": ObjectId(task_id), "user_id": user["_id"]})
        
        if task:
            new_status = not task["completed"]
            mongo.db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": {"completed": new_status}})
            return jsonify({"completed": new_status}), 200
        
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        print(f"❌ Toggle task error: {e}")
        return jsonify({"error": "Failed"}), 500

@app.route("/tasks/delete/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        mongo.db.tasks.delete_one({"_id": ObjectId(task_id), "user_id": user["_id"]})
        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        print(f"❌ Delete task error: {e}")
        return jsonify({"error": "Failed"}), 500

@app.route("/ai-assistant")
def ai_assistant():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("ai_assistant.html")

@app.route("/api/ai/suggest", methods=["POST"])
def ai_suggest():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user = mongo.db.users.find_one({"_id": session["user_id"]})
        data = request.get_json()
        prompt = data.get("prompt", "")
        
        if not prompt:
            return jsonify({"response": "Please ask me something about event planning!"}), 200
        
        # Get smart AI response
        response = get_ai_response(prompt, user["_id"], user["username"])
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ AI suggest error: {e}")
        return jsonify({"response": "I'm having a moment! Please try again."}), 500

# ==================== RUN APP ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 AI EVENT PLANNER STARTING...")
    print("="*60)
    print(f"🌐 Server: http://127.0.0.1:5000")
    print(f"📁 Database: {app.config['MONGO_URI']}")
    print(f"🤖 AI Assistant: Active with Smart Responses")
    print("="*60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
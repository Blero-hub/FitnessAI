import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Configure secret key for session management
app.secret_key = os.urandom(24)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure Google Gemini API key from environment variables
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

# Database Model for User Fitness Plans
class UserPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    activity_level = db.Column(db.String(50), nullable=False)
    dietary_preference = db.Column(db.String(50), nullable=False)
    fitness_goal = db.Column(db.String(50), nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    bmi_category = db.Column(db.String(50), nullable=False)
    tdee = db.Column(db.Float, nullable=False)
    meal_plan_html = db.Column(db.Text, nullable=False)
    workout_plan_html = db.Column(db.Text, nullable=False)
    date_generated = db.Column(db.DateTime, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"UserPlan('{self.age}', '{self.fitness_goal}', '{self.date_generated}', UserID: {self.user_id})"

# Database Model for Users (Authentication)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    plans = db.relationship('UserPlan', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}')"

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Calculates Basal Metabolic Rate (BMR)
def calculate_bmr(gender, weight_kg, height_cm, age):
    if gender == 'male':
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    elif gender == 'female':
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    return bmr

# Calculates Total Daily Energy Expenditure (TDEE)
def calculate_tdee(bmr, activity_level):
    activity_multipliers = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    return bmr * activity_multipliers.get(activity_level, 1.2)

# Sends a prompt to the Gemini API and processes the JSON response
def get_gemini_response(prompt_text):
    try:
        # Using the new client structure
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        raw_text = response.text.strip()
        
        # Clean up markdown if the model includes it despite the JSON config
        if raw_text.startswith('```json'):
            raw_text = raw_text.replace('```json', '', 1).replace('```', '', 1).strip()
            
        return raw_text
    except Exception as e:
        print(f"Error generating content with Gemini: {e}")
        return None

# Generates a meal plan using Gemini API and formats it into HTML
def generate_meal_plan(fitness_goal, dietary_preference, bmi_category, age, gender, activity_level, tdee):
    target_calories = tdee
    calorie_modifier_text = ""
    if fitness_goal == 'lose_weight':
        target_calories = max(1200, tdee - 500)
        calorie_modifier_text = f"Suggest meals for weight loss, aiming for approximately {target_calories:.0f} calories per day."
    elif fitness_goal == 'gain_muscle':
        target_calories += 300
        calorie_modifier_text = f"Suggest meals for muscle gain, aiming for approximately {target_calories:.0f} calories per day."
    else:
        calorie_modifier_text = f"Suggest meals for weight maintenance, aiming for approximately {target_calories:.0f} calories per day."

    prompt = f"""
    You are an AI nutrition expert. Based on the following user data, provide a sample 1-day meal plan.
    Provide the plan as a JSON object.

    User Profile:
    - Fitness Goal: {fitness_goal.replace('_', ' ').title()}
    - Dietary Preference: {dietary_preference.replace('_', ' ').title()}
    - BMI Category: {bmi_category}
    - Age: {age} years
    - Gender: {gender}
    - Activity Level: {activity_level.replace('_', ' ').title()}
    - Estimated TDEE: {tdee:.0f} calories. {calorie_modifier_text}

    JSON Structure Requirements:
    - The root should be a JSON object.
    - It must contain a "title" (string), "introduction" (string), "disclaimer" (string).
    - It must contain a "meals" array, where each object has "type" (e.g., "Breakfast", "Lunch", "Dinner", "Snack"), and "items" (array of strings, e.g., ["2 scrambled eggs", "1 slice whole wheat toast"]).
    - Ensure the JSON is valid and only contains the JSON object, no extra text or markdown code blocks.
    """

    json_response_str = get_gemini_response(prompt)
    if not json_response_str:
        return "<h3>Meal Plan Generation Failed</h3><p>Could not generate meal plan due to an API error or empty response. Please try again.</p>"

    try:
        meal_data = json.loads(json_response_str)
        # Construct HTML output from the parsed JSON data
        html_output = f"<h3>{meal_data.get('title', 'Your Customized Meal Plan')} ({fitness_goal.replace('_', ' ').title()})</h3>"
        html_output += f"<p>Based on your input, your estimated Total Daily Energy Expenditure (TDEE) is **{tdee:.0f} calories**. {calorie_modifier_text} Focus on nutrient-dense foods to meet your targets.</p>"
        html_output += f"<p>{meal_data.get('introduction', '')}</p>"

        for meal in meal_data.get('meals', []):
            html_output += f"<h4>{meal.get('type', 'Meal')}</h4><ul>"
            for item in meal.get('items', []):
                html_output += f"<li>{item}</li>"
            html_output += "</ul>"

        html_output += f"<p><em>{meal_data.get('disclaimer', 'Please consult a healthcare professional or nutritionist before making significant dietary changes.')}</em></p>"
        return html_output
    except json.JSONDecodeError as e:
        print(f"JSON parsing error for meal plan: {e}")
        print(f"Raw response: {json_response_str}")
        return "<h3>Meal Plan Generation Failed</h3><p>There was an error parsing the AI's response for the meal plan. Please try again.</p><p>Error details: " + str(e) + "</p>"
    except Exception as e:
        print(f"Error processing meal plan data: {e}")
        return "<h3>Meal Plan Generation Failed</h3><p>An unexpected error occurred while processing the meal plan.</p><p>Error details: " + str(e) + "</p>"

# Generates a workout plan using Gemini API and formats it into HTML
def generate_workout_plan(fitness_goal, activity_level, bmi_category, age, gender):
    prompt = f"""
    You are an AI fitness coach. Based on the following user data, provide a sample 1-week workout plan.
    Provide the plan as a JSON object.

    User Profile:
    - Fitness Goal: {fitness_goal.replace('_', ' ').title()}
    - Activity Level: {activity_level.replace('_', ' ').title()}
    - BMI Category: {bmi_category}
    - Age: {age} years
    - Gender: {gender}

    JSON Structure Requirements:
    - The root should be a JSON object.
    - It must contain a "title" (string), "introduction" (string), "disclaimer" (string).
    - It must contain a "weekly_schedule" array, where each object has "day" (e.g., "Monday", "Rest Day"), and "description" (string, describing the workout or rest).
    - Ensure the JSON is valid and only contains the JSON object, no extra text or markdown code blocks.
    """

    json_response_str = get_gemini_response(prompt)
    if not json_response_str:
        return "<h3>Workout Plan Generation Failed</h3><p>Could not generate workout plan due to an API error or empty response. Please try again.</p>"

    try:
        workout_data = json.loads(json_response_str)
        # Construct HTML output from the parsed JSON data
        html_output = f"<h3>{workout_data.get('title', 'Your Customized Workout Plan')} ({fitness_goal.replace('_', ' ').title()})</h3>"
        html_output += f"<p>{workout_data.get('introduction', '')}</p>"

        html_output += "<ul>"
        for day_plan in workout_data.get('weekly_schedule', []):
            html_output += f"<li><strong>{day_plan.get('day', 'Day')}:</strong> {day_plan.get('description', '')}</li>"
        html_output += "</ul>"

        html_output += f"<p><em>{workout_data.get('disclaimer', 'Please consult a fitness professional before starting any new workout program.')}</em></p>"
        return html_output
    except json.JSONDecodeError as e:
        print(f"JSON parsing error for workout plan: {e}")
        print(f"Raw response: {json_response_str}")
        return "<h3>Workout Plan Generation Failed</h3><p>There was an error parsing the AI's response for the workout plan. Please try again.</p><p>Error details: " + str(e) + "</p>"
    except Exception as e:
        print(f"Error processing workout plan data: {e}")
        return "<h3>Workout Plan Generation Failed</h3><p>An unexpected error occurred while processing the workout plan.</p><p>Error details: " + str(e) + "</p>"

# Route for the home page
@app.route('/')
def home():
    return render_template('home.html', now=datetime.now())

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('That username is already taken. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', now=datetime.now())

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', now=datetime.now())

# Route for user logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Route to display the plan generation form
@app.route('/generate')
@login_required
def generate_plan_form():
    return render_template('generate_plan_form.html', now=datetime.now())

# Route to process form data and generate fitness plans
@app.route('/generate_plan', methods=['POST'])
@login_required
def generate_plan():
    if request.method == 'POST':
        try:
            # Retrieve and validate form inputs
            age = int(request.form['age'])
            if not (1 <= age <= 120):
                flash('Age must be between 1 and 120.', 'danger')
                return redirect(url_for('generate_plan_form'))

            gender = request.form['gender']
            if gender not in ['male', 'female', 'other']:
                flash('Invalid gender selected.', 'danger')
                return redirect(url_for('generate_plan_form'))

            height_cm = float(request.form['height_cm'])
            if not (50 <= height_cm <= 250):
                flash('Height must be between 50cm and 250cm.', 'danger')
                return redirect(url_for('generate_plan_form'))

            weight_kg = float(request.form['weight_kg'])
            if not (10 <= weight_kg <= 500):
                flash('Weight must be between 10kg and 500kg.', 'danger')
                return redirect(url_for('generate_plan_form'))

            activity_level = request.form['activity_level']
            if activity_level not in ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extra_active']:
                flash('Invalid activity level selected.', 'danger')
                return redirect(url_for('generate_plan_form'))

            dietary_preference = request.form['dietary_preference']
            fitness_goal = request.form['fitness_goal']
            if fitness_goal not in ['lose_weight', 'maintain_weight', 'gain_muscle']:
                flash('Invalid fitness goal selected.', 'danger')
                return redirect(url_for('generate_plan_form'))

            # Calculate BMI and TDEE
            height_m = height_cm / 100
            bmi = weight_kg / (height_m ** 2)

            bmi_category = ""
            if bmi < 18.5:
                bmi_category = "Underweight"
            elif 18.5 <= bmi < 24.9:
                bmi_category = "Normal weight"
            elif 25 <= bmi < 29.9:
                bmi_category = "Overweight"
            else:
                bmi_category = "Obese"

            bmr = calculate_bmr(gender, weight_kg, height_cm, age)
            tdee = calculate_tdee(bmr, activity_level)

            # Generate meal and workout plans using AI
            meal_plan = generate_meal_plan(fitness_goal, dietary_preference, bmi_category, age, gender, activity_level, tdee)
            workout_plan = generate_workout_plan(fitness_goal, activity_level, bmi_category, age, gender)

            # Handle cases where AI generation might fail
            if "Generation Failed" in meal_plan or "Generation Failed" in workout_plan:
                flash("One or both plans failed to generate. This might be due to an API error or an unparsable response from the AI. Please try again.", 'danger')
                return redirect(url_for('generate_plan_form'))

            # Save the new plan to the database
            new_plan = UserPlan(
                age=age,
                gender=gender,
                height_cm=height_cm,
                weight_kg=weight_kg,
                activity_level=activity_level,
                dietary_preference=dietary_preference,
                fitness_goal=fitness_goal,
                bmi=bmi,
                bmi_category=bmi_category,
                tdee=tdee,
                meal_plan_html=meal_plan,
                workout_plan_html=workout_plan,
                user_id=current_user.id
            )
            db.session.add(new_plan)
            db.session.commit()
            flash(f"Your plan (ID: {new_plan.id}) has been saved!", 'success')

            session['last_plan_id'] = new_plan.id # Store the ID of the newly generated plan in session

            # Render results page with generated plans and user data
            return render_template(
                'results.html',
                bmi=f"{bmi:.2f}",
                bmi_category=bmi_category,
                tdee=f"{tdee:.0f}",
                meal_plan=meal_plan,
                workout_plan=workout_plan,
                user_data={
                    'age': age, 'gender': gender, 'height_cm': height_cm,
                    'weight_kg': weight_kg, 'activity_level': activity_level,
                    'dietary_preference': dietary_preference, 'fitness_goal': fitness_goal
                },
                now=datetime.now()
            )

        except ValueError as ve:
            print(f"Validation error on form input: {ve}")
            flash(f"Invalid input provided. Please ensure all numerical fields are correct and try again. Error: {ve}", 'danger')
            return redirect(url_for('generate_plan_form'))
        except Exception as e:
            print(f"Unhandled error processing form submission: {e}")
            flash(f"An unexpected error occurred: {e}. Please try again.", 'danger')
            return redirect(url_for('generate_plan_form'))

    return redirect(url_for('generate_plan_form'))

# Route to view all saved fitness plans for the current user
@app.route('/view_plans')
@login_required
def view_plans():
    all_plans = UserPlan.query.filter_by(user_id=current_user.id).order_by(UserPlan.date_generated.desc()).all()
    return render_template('view_plans.html', all_plans=all_plans, now=datetime.now())

# Route to edit an existing fitness plan
@app.route('/edit_plan/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def edit_plan(plan_id):
    plan = UserPlan.query.get_or_404(plan_id)
    # Ensure the current user is authorized to edit this plan
    if plan.user_id != current_user.id:
        flash('You are not authorized to edit this plan.', 'danger')
        return redirect(url_for('view_plans'))

    if request.method == 'POST':
        try:
            # Update plan attributes from form data and re-validate
            plan.age = int(request.form['age'])
            if not (1 <= plan.age <= 120):
                flash('Age must be between 1 and 120.', 'danger')
                return redirect(url_for('edit_plan', plan_id=plan.id))

            plan.gender = request.form['gender']
            if plan.gender not in ['male', 'female', 'other']:
                flash('Invalid gender selected.', 'danger')
                return redirect(url_for('edit_plan', plan_id=plan.id))

            plan.height_cm = float(request.form['height_cm'])
            if not (50 <= plan.height_cm <= 250):
                flash('Height must be between 50cm and 250cm.', 'danger')
                return redirect(url_for('edit_plan', plan_id=plan.id))

            plan.weight_kg = float(request.form['weight_kg'])
            if not (10 <= plan.weight_kg <= 500):
                flash('Weight must be between 10kg and 500kg.', 'danger')
                return redirect(url_for('edit_plan', plan_id=plan.id))

            plan.activity_level = request.form['activity_level']
            if plan.activity_level not in ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extra_active']:
                flash('Invalid activity level selected.', 'danger')
                return redirect(url_for('edit_plan', plan_id=plan.id))

            plan.dietary_preference = request.form['dietary_preference']
            plan.fitness_goal = request.form['fitness_goal']
            if plan.fitness_goal not in ['lose_weight', 'maintain_weight', 'gain_muscle']:
                flash('Invalid fitness goal selected.', 'danger')
                return redirect(url_for('edit_plan', plan_id=plan.id))

            # Recalculate BMI and TDEE based on updated inputs
            height_m = plan.height_cm / 100
            plan.bmi = plan.weight_kg / (height_m ** 2)

            if plan.bmi < 18.5:
                plan.bmi_category = "Underweight"
            elif 18.5 <= plan.bmi < 24.9:
                plan.bmi_category = "Normal weight"
            elif 25 <= plan.bmi < 29.9:
                plan.bmi_category = "Overweight"
            else:
                plan.bmi_category = "Obese"

            bmr = calculate_bmr(plan.gender, plan.weight_kg, plan.height_cm, plan.age)
            plan.tdee = calculate_tdee(bmr, plan.activity_level)

            # Regenerate meal and workout plans using the updated data
            plan.meal_plan_html = generate_meal_plan(
                plan.fitness_goal, plan.dietary_preference, plan.bmi_category,
                plan.age, plan.gender, plan.activity_level, plan.tdee
            )
            plan.workout_plan_html = generate_workout_plan(
                plan.fitness_goal, plan.activity_level, plan.bmi_category,
                plan.age, plan.gender
            )

            # Handle regeneration failure
            if "Generation Failed" in plan.meal_plan_html or "Generation Failed" in plan.workout_plan_html:
                flash("One or both plans failed to regenerate. Please review your inputs and try again.", 'danger')
                return redirect(url_for('edit_plan', plan_id=plan.id))

            plan.date_generated = datetime.now()

            db.session.commit()
            flash('Plan updated successfully!', 'success')
            return redirect(url_for('view_plans'))

        except ValueError as ve:
            flash(f"Invalid input provided. Please ensure all numerical fields are correct. Error: {ve}", 'danger')
            return redirect(url_for('edit_plan', plan_id=plan.id))
        except Exception as e:
            flash(f"Error updating plan: {e}", 'danger')
            return redirect(url_for('edit_plan', plan_id=plan.id))
    
    return render_template('edit_plan.html', plan=plan, now=datetime.now())

# Route to delete a fitness plan
@app.route('/delete_plan/<int:plan_id>', methods=['POST'])
@login_required
def delete_plan(plan_id):
    plan = UserPlan.query.get_or_404(plan_id)
    # Ensure the current user is authorized to delete this plan
    if plan.user_id != current_user.id:
        flash('You are not authorized to delete this plan.', 'danger')
        return redirect(url_for('view_plans'))

    try:
        db.session.delete(plan)
        db.session.commit()
        flash('Plan deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting plan: {e}', 'danger')
    
    return redirect(url_for('view_plans'))

# Entry point for running the Flask application
if __name__ == '__main__':
    # Create database tables within the application context on startup
    with app.app_context():
        db.create_all()
    app.run(debug=True)
AI Fitness Generator
Video Demo: https://youtu.be/DEKg8PDQjMM
Description:

The AI Fitness Generator is a comprehensive full-stack web application designed to empower individuals on their health and wellness journey. It offers a personalized approach to fitness and nutrition by generating tailored meal and workout plans. Built using Python Flask and standard web technologies (HTML, CSS, JavaScript), the application leverages the advanced capabilities of the Google Gemini API to produce dynamic and highly customized content. Its core aim is to simplify the often complex process of planning effective fitness and dietary strategies, making a healthier lifestyle more accessible and manageable for a wide range of users with varying goals and preferences. Users can seamlessly create accounts, log in, generate new plans based on their unique profiles, and then save, review, or modify these plans over time, ensuring consistent, accessible tracking of their fitness journey.

Key Features:
Secure User Authentication: Implements Flask-Login for secure registration, login, and logout. Passwords are hashed with werkzeug.security. Access to features is restricted to logged-in users, ensuring data privacy.

Personalized Plan Generation: A user-friendly form collects age, gender, height, weight, activity level, dietary preferences, and fitness goals for highly individualized plan creation.

Automated Health Metrics Calculation: Automatically calculates Body Mass Index (BMI) and Total Daily Energy Expenditure (TDEE) from user input, informing calorie targets and weight status.

AI-Powered Content Generation: app.py interacts with Google Gemini 1.5 Flash API. Dynamic prompts based on user profiles generate tailored 1-day meal and 1-week workout plans as structured JSON.

Persistent Plan Storage: All generated plans and user data are saved to an SQLite database via Flask-SQLAlchemy, allowing users to track progress and review past recommendations.

Comprehensive Plan Management: A "View Plans" section lists saved plans chronologically, offering options to view full details, edit input parameters (and regenerate AI content), or delete plans.

Intuitive User Interface: Frontend uses HTML, CSS, and JavaScript for clear navigation, easy data input, and understanding of generated plans.

Robust Error Handling and Validation: Includes client-side JavaScript validation for immediate feedback and server-side try-except blocks for graceful handling of API and parsing errors, ensuring application stability.

Files in the Project:
app.py: The central Flask application file handling routing, database interactions, and Gemini API integration. It defines user and plan models, calculates health metrics, generates AI responses (meal/workout plans), and manages all application routes.

templates/: Contains Jinja2 HTML templates for all web pages: home.html, register.html, login.html, generate_plan_form.html, results.html, view_plans.html, and edit_plan.html.

static/: Holds static assets: style.css for visual design and responsive layout, and script.js for client-side validation, loading overlays, and "Show Details" toggles.

site.db: The SQLite database file, managed by SQLAlchemy, storing all user accounts and their fitness plans persistently.

requirements.txt: This file lists all the Python libraries required for the project to run, enabling easy installation of dependencies.

How to Run the Application (on CS50.dev):
Open your CS50.dev workspace.

Navigate to your project directory in the terminal. For example, if your app.py is in a folder named FitnessAI (or the root of your project):

cd FitnessAI

Install necessary Python packages. It's recommended to do this in a virtual environment. CS50.dev often handles virtual environments automatically, but you can explicitly create and activate one if needed:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Set your Google Gemini API Key. Since .env files are not part of the submission and are for local development, you'll need to set your API key as an environment variable directly in the CS50.dev terminal session before running the app:

export GOOGLE_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY_HERE"

Replace "YOUR_ACTUAL_GEMINI_API_KEY_HERE" with your real API key. This command sets the variable for the current terminal session.

Run the Flask application:

flask run

or

python app.py

Open the web application. CS50.dev will provide a URL (usually accessible via "Open in Browser" or a port link) to view your running application.

Design Choices and Challenges:
A key challenge was reliably parsing JSON from the Google Gemini API, which sometimes included Markdown wrappers or non-JSON text. This was resolved by explicitly setting response_mime_type="application/json" in the API call and implementing conditional logic in get_gemini_response to strip any remaining Markdown. Enhanced error logging during JSON decoding was crucial for debugging. Flask-Login was chosen for secure user authentication, leveraging its robust framework over building from scratch. SQLite was selected for its simplicity in local development. The modular architecture separates concerns, improving readability, maintainability, and testability, while client-side validation enhances user experience.
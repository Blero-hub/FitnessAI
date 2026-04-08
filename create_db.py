from app import app, db

# Ensure the Flask application context is active
with app.app_context():
    db.create_all()
    print("Database tables created!")
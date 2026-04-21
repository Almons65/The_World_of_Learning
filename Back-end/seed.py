import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import db
from models import User, Folder, LearningVideo
import transaction
def seed_database():
    print("Starting database seeding...")
    db.root['users'] = {}
    demo_user = User("demo", "demo@example.com", "Demo@1234!")
    demo_user.interests = ["Software Engineering", "Artificial Intelligence"]
    v1 = LearningVideo("vid-1", "Introduction to OOP in Python", "12:00 min • Codecademy", "Software Engineering", "https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=400&auto=format&fit=crop", "/home")
    v2 = LearningVideo("vid-2", "Composite Design Pattern", "18:45 min • Refactoring.Guru", "Software Engineering", "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=400&auto=format&fit=crop", "/home")
    v3 = LearningVideo("vid-3", "FastAPI Full Course", "2:30:00 hr • FreeCodeCamp", "Web Development", "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&auto=format&fit=crop", "/home")
    v4 = LearningVideo("vid-4", "What is Generative AI?", "8:20 min • Google Cloud", "Artificial Intelligence", "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400&auto=format&fit=crop", "/home")
    v5 = LearningVideo("vid-5", "Build a Chatbot with Gemini", "25:10 min • Google Developers", "Artificial Intelligence", "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400&auto=format&fit=crop", "/home")
    eng_folder = Folder("Engineering Archive", True)
    eng_sub1 = Folder("Design Patterns")
    eng_sub2 = Folder("Frameworks")
    eng_sub1.add_item(v1)
    eng_sub1.add_item(v2)
    eng_sub2.add_item(v3)
    eng_folder.add_item(eng_sub1)
    eng_folder.add_item(eng_sub2)
    ai_folder = Folder("AI Modules", True)
    ai_sub1 = Folder("Concepts")
    ai_sub2 = Folder("Applied AI")
    ai_sub1.add_item(v4)
    ai_sub2.add_item(v5)
    ai_folder.add_item(ai_sub1)
    ai_folder.add_item(ai_sub2)
    demo_user.folders["Engineering Archive"] = eng_folder
    demo_user.folders["AI Modules"] = ai_folder
    demo_user.history = [v1.to_dict(), v4.to_dict()]
    db.root['users']["demo"] = demo_user
    db.commit()
    print("Database seeding completed.")
    print("Test User: username: 'demo', password: 'Demo@1234!'")
if __name__ == "__main__":
    seed_database()

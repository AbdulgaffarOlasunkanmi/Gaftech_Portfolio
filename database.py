from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "portfolio_db")

# Collections
CONTACT_COLLECTION = os.getenv("CONTACT_COLLECTION", "contacts")
ADMIN_COLLECTION = os.getenv("ADMIN_COLLECTION", "admins")
PROJECTS_COLLECTION = os.getenv("PROJECTS_COLLECTION", "projects")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

contact_collection = db[CONTACT_COLLECTION]
admin_collection = db[ADMIN_COLLECTION]
projects_collection = db[PROJECTS_COLLECTION]

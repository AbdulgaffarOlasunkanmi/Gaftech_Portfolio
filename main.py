from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends,
    HTTPException,
    status,
    File,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os
import traceback
import shutil
import uuid

from schemas import ContactFormSchema
from database import contact_collection, admin_collection, projects_collection
from auth import hash_password, verify_password, create_access_token
from deps import get_current_admin
from serializers import contact_list_serializer

# -------------------------------------------------------------
# Initialization
# -------------------------------------------------------------
load_dotenv()
app = FastAPI(title="Portfolio Contact Admin Dashboard")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Upload directory
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -------------------------------------------------------------
# Create Default Admin on Startup
# -------------------------------------------------------------
@app.on_event("startup")
def create_default_admin():
    """Create the default admin if not existing."""
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username or not admin_password:
        print("ADMIN_USERNAME or ADMIN_PASSWORD not set in .env")
        return

    existing_admin = admin_collection.find_one({"username": admin_username})
    if not existing_admin:
        admin_collection.insert_one(
            {"username": admin_username, "password": hash_password(admin_password)}
        )
        print(f"Default admin '{admin_username}' created.")
    else:
        print(f"Admin '{admin_username}' already exists.")


# -------------------------------------------------------------
# Public Routes
# -------------------------------------------------------------
# @app.get("/", response_class=HTMLResponse)
# def index(request: Request, success: str = None, error: str = None):
#    """Homepage (contact form)"""
#    return templates.TemplateResponse(
#        "index.html", {"request": request, "success": success, "error": error}
#    )


@app.post("/contact/form")
def contact_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
):
    """Handle contact form submission"""
    try:
        data = ContactFormSchema(
            name=name,
            email=email,
            subject=subject,
            message=message,
            created_at=datetime.utcnow(),
        )
        contact_collection.insert_one(data.dict())
        return RedirectResponse(url="/?success=true", status_code=303)

    except Exception as e:
        print("Contact form submission failed:", e)
        traceback.print_exc()
        return RedirectResponse(url="/?error=true#contact", status_code=303)


# -------------------------------------------------------------
# Admin Login
# -------------------------------------------------------------
@app.get("/admin", response_class=HTMLResponse)
def login_page(request: Request):
    """Render the admin login page"""
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/admin/login")
def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authenticate admin and set JWT cookie"""
    admin = admin_collection.find_one({"username": username})
    if admin and verify_password(password, admin["password"]):
        token = create_access_token({"sub": username})
        response = RedirectResponse(url="/admin/messages", status_code=303)
        response.set_cookie(key="access_token", value=token, httponly=True)
        return response

    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": "Invalid username or password"},
    )


# -------------------------------------------------------------
# Admin Message Dashboard
# -------------------------------------------------------------
@app.get("/admin/messages", response_class=HTMLResponse)
def admin_messages(
    request: Request,
    admin: str = Depends(get_current_admin),
    search: str = None,
    page: int = 1,
    limit: int = 10,
):
    """Render admin message dashboard with pagination & search"""
    try:
        query = {}
        if search:
            query = {
                "$or": [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}},
                    {"subject": {"$regex": search, "$options": "i"}},
                    {"message": {"$regex": search, "$options": "i"}},
                ]
            }

        total_messages = contact_collection.count_documents(query)
        total_pages = (total_messages + limit - 1) // limit

        messages_cursor = (
            contact_collection.find(query)
            .sort("created_at", -1)
            .skip((page - 1) * limit)
            .limit(limit)
        )

        messages = []
        for msg in messages_cursor:
            msg["_id"] = str(msg["_id"])
            created_at = msg.get("created_at")
            if isinstance(created_at, str):
                try:
                    msg["created_at"] = datetime.fromisoformat(created_at)
                except Exception:
                    msg["created_at"] = datetime.utcnow()
            elif not isinstance(created_at, datetime):
                msg["created_at"] = datetime.utcnow()
            messages.append(msg)

        return templates.TemplateResponse(
            "admin_message.html",
            {
                "request": request,
                "messages": contact_list_serializer(messages),
                "page": page,
                "total_pages": total_pages,
                "search": search or "",
            },
        )

    except Exception as e:
        print("/admin/messages failed:", e)
        traceback.print_exc()
        return HTMLResponse(f"<h3>Internal Server Error: {e}</h3>", status_code=500)


# -------------------------------------------------------------
# Delete Message
# -------------------------------------------------------------
@app.post("/admin/delete/{message_id}")
def delete_message(message_id: str, admin: str = Depends(get_current_admin)):
    """Delete message by ID"""
    try:
        result = contact_collection.delete_one({"_id": ObjectId(message_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Message not found")

        return RedirectResponse(url="/admin/messages", status_code=303)

    except Exception as e:
        print("Failed to delete message:", e)
        traceback.print_exc()
        return HTMLResponse(f"<h3>Error deleting message: {e}</h3>", status_code=500)


# -------------------------------------------------------------
# Logout
# -------------------------------------------------------------
@app.get("/admin/logout")
def admin_logout():
    """Logout admin by clearing cookie"""
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("access_token")
    return response


# -------------------------------------------------------------
# PROJECTS
# -------------------------------------------------------------


# -------------------------------------------------------------
# Upload Project Page (GET)
# -------------------------------------------------------------
@app.get("/admin/upload")
async def admin_upload_page(request: Request):
    return templates.TemplateResponse("admin_upload.html", {"request": request})


# -------------------------------------------------------------
# Upload Project (POST)
# -------------------------------------------------------------
@app.post("/admin/upload-project")
async def upload_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    link: str = Form(None),
    image: UploadFile = File(...),
):

    # Allowed formats
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use PNG, JPG, JPEG, or WEBP."
        )

    # Generate unique filename
    ext = image.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    # Save image to /static/uploads/
    save_path = f"static/uploads/{filename}"

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Image URL for frontend (correct path!)
    image_url = f"/static/uploads/{filename}"

    project = {
        "title": title,
        "description": description,
        "category": category,
        "image_url": image_url,
        "link": link if link else "#",
        "created_at": datetime.utcnow(),
    }

    projects_collection.insert_one(project)

    return RedirectResponse("/admin/projects", status_code=302)


# -----------------------------
# Admin: View Projects
# -----------------------------
@app.get("/admin/projects", response_class=HTMLResponse)
async def view_projects(request: Request):
    projects = list(projects_collection.find().sort("created_at", -1))

    for p in projects:
        p["_id"] = str(p["_id"])

    return templates.TemplateResponse(
        "admin_projects.html", {"request": request, "projects": projects}
    )


# -----------------------------
# Admin: Upload Project Form
# -----------------------------
@app.get("/admin/upload-project", response_class=HTMLResponse)
async def upload_project_form(request: Request):
    return templates.TemplateResponse("upload_project.html", {"request": request})


# -----------------------------
# Admin: Edit Project
# -----------------------------
@app.get("/admin/edit/{project_id}", response_class=HTMLResponse)
async def edit_project_form(request: Request, project_id: str):
    project = projects_collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project["_id"] = str(project["_id"])
    return templates.TemplateResponse(
        "admin_edit.html", {"request": request, "project": project}
    )


@app.post("/admin/update/{project_id}")
async def edit_project(
    project_id: str,
    title: str = Form(...),
    description: str = Form(...),
    link: str = Form(None),
):
    update = {"title": title, "description": description, "link": link or "#"}
    result = projects_collection.update_one(
        {"_id": ObjectId(project_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return RedirectResponse("/admin/projects", status_code=302)


# -----------------------------
# Admin: Delete Project
# -----------------------------
@app.get("/admin/delete/{project_id}")
async def delete_project(project_id: str):
    result = projects_collection.delete_one({"_id": ObjectId(project_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return RedirectResponse("/admin/projects", status_code=302)


# -------------------------------------------------------------
# Portfolio (Frontend)
# -------------------------------------------------------------


# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):

# Fetch projects from MongoDB (sorted newest first)
#   projects_cursor = projects_collection.find().sort("created_at", -1)
#    projects = []

#    for project in projects_cursor:
#        project["_id"] = str(project["_id"])  # Convert ObjectId -> string

#        # Ensure missing fields do not break the HTML
#        project.setdefault("title", "Untitled Project")
#        project.setdefault("category", "General")
#        project.setdefault("image_url", "/static/default.jpg")
#        project.setdefault("description", "")

#        projects.append(project)

#    return templates.TemplateResponse(
#        "index.html", {"request": request, "projects": projects}
#    )


# -------------------------------------------------------------
# Public Routes (Combined Logic)
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, success: str = None, error: str = None):
    """Homepage (contact form & portfolio projects)"""

    # Fetch projects from MongoDB (sorted newest first)
    projects_cursor = projects_collection.find().sort("created_at", -1)
    projects = []

    for project in projects_cursor:
        project["_id"] = str(project["_id"])  # Convert ObjectId -> string

        # Ensure missing fields do not break the HTML
        project.setdefault("title", "Untitled Project")

        # NOTE: Your admin_upload.html uses a 'category' field,
        # but your upload logic doesn't save it and your index.html uses no category filter.
        # For now, we'll default to 'General' to prevent an error if you add filtering later.
        project.setdefault("category", "General")

        project.setdefault(
            "image_url", "/static/default.jpg"
        )  # Assuming you have a default image
        project.setdefault("description", "")

        projects.append(project)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "success": success,
            "error": error,
            "projects": projects,  # <-- This is the crucial context variable
        },
    )

from datetime import datetime

# ------------------------
# CONTACT SERIALIZER


def contact_serializer(contact) -> dict:
    return {
        "id": str(contact["_id"]),
        "name": contact["name"],
        "email": contact["email"],
        "subject": contact["subject"],
        "message": contact["message"],
        "created_at": contact["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
    }


def contact_list_serializer(contacts) -> list:
    return [contact_serializer(contact) for contact in contacts]

# ------------------------
# PROJECT SERIALIZER
# ------------------------


def project_serializer(project) -> dict:
    return {
        "id": str(project["_id"]),
        "title": project["title"],
        "description": project["description"],
        "image_url": project["image_url"],
        "link": project["link"],
        "created_at": project["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
    }


def project_list_serializer(projects) -> list:
    return [project_serializer(project) for project in projects]

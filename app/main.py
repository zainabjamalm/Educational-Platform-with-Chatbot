from fastapi import FastAPI, HTTPException, Depends, status,Query
from pydantic import BaseModel
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash
#from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import os
import json
from config import api, url
from app.ClassModels import *
app = FastAPI()
supabase = create_client(url, api)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data")

#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # not using token-based login for now
@app.get("/")
def index():
    return "Welcome to out AI Platform!"

@app.post("/register")
def register(user: UserRegister):
    existing = supabase.table("Users").select("email").eq("email", user.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = generate_password_hash(user.password)
    new_user = { "email": user.email, "username": user.username, "password": hashed_pw,"role": user.role}

    response = supabase.table("Users").insert(new_user).execute()
    if response.error:
        raise HTTPException(status_code=500, detail=f"Supabase error: {response.error.message}")
    
    return {"message": "User registered successfully"}

@app.post("/login")
def login(user: UserLogin):
    response = supabase.table("Users").select("*").eq("email", user.email).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    db_user = response.data[0]
    if not check_password_hash(db_user["password"], user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return {
        "message": "Login successful",
        "user": {
            "user_id": db_user["user_id"],"email": db_user["email"],
            "username": db_user["username"],"role": db_user["role"] }}

def check_admin(user_id: int):
    response = supabase.table("Users").select("role").eq("user_id", user_id).execute()
    if not response.data or response.data[0]["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden. Admins only.")

def check_student(user_id: int):
    res = supabase.table("Users").select("role").eq("user_id", user_id).single().execute()
    if res.error:
        raise HTTPException(status_code=404, detail="User not found")
    if res.data["role"] != "student":
        raise HTTPException(status_code=403, detail="Access restricted to students only")


@app.get("/admin/users")
def get_all_users(admin_id: int):
    check_admin(admin_id)
    users = supabase.table("Users").select("user_id,email,username,role").execute()
    return users.data

@app.get("/admin/users/{user_id}")
def get_user(user_id: int, admin_id: int):
    check_admin(admin_id)
    user = supabase.table("Users").select("user_id,email,username,role").eq("user_id", user_id).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    return user.data[0]

@app.put("/admin/users/{user_id}")
def update_user(user_id: int, data: dict, admin_id: int):
    check_admin(admin_id)
    res = supabase.table("Users").update(data).eq("user_id", user_id).execute()
    return {"message": "User updated", "data": res.data}

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, admin_id: int):
    check_admin(admin_id)
    supabase.table("Users").delete().eq("user_id", user_id).execute()
    return {"message": "User deleted"}



@app.post("/admin/courses")
def create_course(course: CourseModel, admin_id: int):
    check_admin(admin_id)
    res = supabase.table("Courses").insert(course.dict()).execute()
    return {"message": "Course created", "data": res.data}

@app.get("/admin/courses")
def list_courses(admin_id: int):
    check_admin(admin_id)
    res = supabase.table("Courses").select("*").execute()
    return res.data

@app.get("/admin/courses/{course_id}")
def get_course(course_id: int, admin_id: int):
    check_admin(admin_id)
    res = supabase.table("Courses").select("*").eq("course_id", course_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Course not found")
    return res.data[0]

@app.put("/admin/courses/{course_id}")
def update_course(course_id: int, updates: dict, admin_id: int):
    check_admin(admin_id)
    res = supabase.table("Courses").update(updates).eq("course_id", course_id).execute()
    return {"message": "Course updated", "data": res.data}

@app.delete("/admin/courses/{course_id}")
def delete_course(course_id: int, admin_id: int):
    check_admin(admin_id)
    supabase.table("Courses").delete().eq("course_id", course_id).execute()
    return {"message": "Course deleted"}
#common api
@app.get("/courses/{course_id}/content")
def get_course_content(course_id: int):
    response = supabase.table("Course_Content").select("*").eq("course_id", course_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="No lessons found for this course.")
    return response.data



#students
@app.get("/student/{user_id}/enrolled-courses")
def get_enrolled_courses(user_id: int):
    check_student(user_id)
    response = supabase.table("User_Courses")\
        .select("course_id, Courses(course_title, course_description)")\
        .eq("user_id", user_id)\
        .execute()
    
    if response.error:
        raise HTTPException(status_code=500, detail=f"Supabase error: {response.error.message}")
    return response.data

@app.post("/student/{user_id}/enroll/{course_id}")
def enroll_in_course(user_id: int, course_id: int):
    check_student(user_id)

    existing = supabase.table("User_Courses")\
        .select("enrollment_id")\
        .eq("user_id", user_id)\
        .eq("course_id", course_id)\
        .execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    enrollment_data = {
        "user_id": user_id,"course_id": course_id,"progress": 0.0,"status": "enrolled",
        "enrollment_at": datetime.utcnow().isoformat()}
    response = supabase.table("User_Courses").insert(enrollment_data).execute()
    if response.error:
        raise HTTPException(status_code=500, detail=f"Supabase error: {response.error.message}")
    return {"message": "Enrolled successfully", "data": response.data}


@app.get("/student/{user_id}/available-courses")
def get_available_courses(user_id: int):
    check_student(user_id)
    enrolled = supabase.table("User_Courses")\
        .select("course_id")\
        .eq("user_id", user_id)\
        .execute()
    if enrolled.error:
        raise HTTPException(status_code=500, detail=f"Supabase error: {enrolled.error.message}")

    enrolled_ids = [row["course_id"] for row in enrolled.data]

    if not enrolled_ids:
        response = supabase.table("Courses").select("*").execute()
    else:
        response = supabase.table("Courses").select("*").not_.in_("course_id", enrolled_ids).execute()
    return response.data

@app.delete("/student/{user_id}/unenroll/{course_id}")
def unenroll_from_course(user_id: int, course_id: int):
    check_student(user_id)
    check = supabase.table("User_Courses")\
        .select("enrollment_id")\
        .eq("user_id", user_id)\
        .eq("course_id", course_id)\
        .execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    res = supabase.table("User_Courses")\
        .delete()\
        .eq("user_id", user_id)\
        .eq("course_id", course_id)\
        .execute()
    if res.error:
        raise HTTPException(status_code=500, detail=f"Supabase error: {res.error.message}")
    return {"message": "Unenrolled successfully"}

@app.post("/seed/courses")
def seed_multiple_courses(admin_id: int):
    check_admin(admin_id)
    try:
        with open(os.path.join(DATA_DIR, "course_data.json"), "r", encoding="utf-8") as f:
            courses_data = json.load(f)

        for course_data in courses_data:
            course = supabase.table("Courses").select("*").eq("course_id", course_data["course_id"]).execute()
            if course.data:
                print(f"Course ID {course_data['course_id']} already exists. Skipping.")
                continue

            supabase.table("Courses").insert({
                "course_id": course_data["course_id"],
                "course_title": course_data["course_title"],
                "course_description": course_data["course_description"],
                "prerequisites": course_data["prerequisites"],
                "tags": course_data["tags"]
            }).execute()

            for lesson_data in course_data.get("lessons", []):
                try:
                    with open(f"../Data/{lesson_data['content']}", "r") as f:
                        content = f.read()
                except FileNotFoundError:
                    content = "Content file not found."

                supabase.table("Course_Content").insert({
                    "course_id": course_data["course_id"],
                    "lesson_id": lesson_data["lesson_id"],
                    "lesson_title": lesson_data["lesson_title"],
                    "lesson_description": lesson_data["lesson_description"],
                    "content": content
                }).execute()

        return {"message": "All courses seeded successfully."}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="course_data.json not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding courses: {str(e)}")
    
@app.post("/seed/users")
def seed_user_data(admin_id: int = Query(...)):
    check_admin(admin_id)

    try:
        with open(os.path.join(DATA_DIR, "user_data.json"), "r", encoding="utf-8") as f:
            users_data = json.load(f)

        for user in users_data:
            exists = supabase.table("Users").select("username").eq("username", user["username"]).execute()
            if exists.data:
                print(f"User {user['username']} already exists. Skipping.")
                continue

            hashed_pw = user["password"]

            supabase.table("Users").insert({
                "username": user["username"],
                "email": user["email"],
                "password": hashed_pw,
                "role": user.get("role", "student")
            }).execute()

        return {"message": "User data seeded successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="users_data.json not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding user data: {str(e)}")
    
@app.post("/seed/usercourses")
def seed_user_courses(admin_id: int):
    check_admin(admin_id)
    try:
        file_path = os.path.join(DATA_DIR, "user_courses_data.json")
        with open(file_path, "r", encoding="utf-8") as f:
            user_courses_data = json.load(f)

        for record in user_courses_data:
            exists = supabase.table("User_Courses").select("enrollment_id")\
                .eq("user_id", record["user_id"])\
                .eq("course_id", record["course_id"])\
                .execute()

            if exists.data:
                print(f"Enrollment already exists for user_id={record['user_id']} and course_id={record['course_id']}. Skipping.")
                continue
            supabase.table("User_Courses").insert(record).execute()

        return {"message": "User_Courses data seeded successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="user_courses_data.json not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding User_Courses data: {str(e)}")
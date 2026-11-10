"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from datetime import datetime
from django.utils.dateparse import parse_time
from django.utils import timezone

import zoneinfo
import json
import io
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import InstructorProfile, StudentProfile, Course, Lecture, QRCodeUpload


def get_instructor(user):
    """Return the user's InstructorProfile, or None if they aren't an instructor."""
    if not user.is_authenticated:
        return None
    return InstructorProfile.objects.filter(user=user).first()

def get_student(user):
    """Return the user's StudentProfile, or None if they aren't a student."""
    if not user.is_authenticated:
        return None
    return StudentProfile.objects.filter(user=user).first()

# from .models import (InstructorProfile, StudentProfile, Course, Enrollment,
#                      Lecture, QRCodeUpload, is_instructor, is_student,
#                      getUploadsForCourse)

CDT = zoneinfo.ZoneInfo("America/Chicago")

# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    """Render the home page (index.html)."""

    context = {}
    return render(request, 'app/index.html', context)

def time_view(request):
    now = datetime.now(CDT)
    return HttpResponse(now.strftime("%H:%M"), content_type="text/plain")

def to_number(text):
    try:
        return int(text)
    except ValueError:
        return float(text)

def sum_view(request):
    n1 = to_number(request.GET["n1"])
    n2 = to_number(request.GET["n2"])
    return HttpResponse(f"<p>{n1 + n2}</p>")

# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------

def index(request):
    now = datetime.now(CDT)

    if request.user.is_authenticated:
        username = request.user.username
    else:
        username = None

    context = {
        "current_time": now.strftime("%H:%M"),
        "username": username,
    }
    return render(request, "app/index.html", context)


@require_GET
def new(request):
    return render(request, "app/new.html")

@csrf_exempt

@require_POST
def createUser(request):
    email = request.POST.get("email")
    user_name = request.POST.get("user_name")
    password = request.POST.get("password")
    is_student = request.POST.get("is_student")

    # Make sure all four fields were sent
    if not email or not user_name or not password or is_student is None:
        return HttpResponseBadRequest("Missing required fields.")

    # Reject duplicate emails
    if User.objects.filter(email=email).exists():
        return HttpResponseBadRequest("A user with that email already exists.")

    # Usernames must also be unique in Django
    if User.objects.filter(username=user_name).exists():
        return HttpResponseBadRequest("That username is taken.")

    # Create the Django user (password gets hashed automatically)
    user = User.objects.create_user(username=user_name, email=email, password=password)

    # Create the matching profile
    if is_student == "1":
        StudentProfile.objects.create(user=user, name=user_name)
    else:
        InstructorProfile.objects.create(user=user, name=user_name)

    # Sign the new user in
    login(request, user)

    return HttpResponse("User created successfully.", status=200)

# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------

from django.shortcuts import render
from .models import Course

def new_course(request):
    return render(request, "app/new_course.html")

def new_lecture(request):
    courses = Course.objects.all()
    return render(request, "app/new_lecture.html", {"courses": courses})

def new_qr_upload(request):
    return render(request, "app/new_qr_upload.html")

@csrf_exempt
def createCourse(request):
    # 1. Authorization first, before anything touches the database
    instructor = get_instructor(request.user)
    if instructor is None:
        return HttpResponse("Unauthorized", status=401)

    # 2. Only POST is allowed
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    # 3. Read and validate the form data
    name = request.POST.get("course-name", "").strip()
    if not name:
        return HttpResponse("Missing course-name", status=400)

    try:
        start_time = parse_time(request.POST.get("start-time", ""))
        end_time = parse_time(request.POST.get("end-time", ""))
    except ValueError:
        start_time = end_time = None
    if start_time is None or end_time is None:
        return HttpResponse("Invalid start-time or end-time", status=400)

    # 4. Turn the checkboxes into a string like "MWF"
    day_fields = [
        ("day-mon", "M"),
        ("day-tue", "T"),
        ("day-wed", "W"),
        ("day-thu", "R"),
        ("day-fri", "F"),
    ]
    meeting_days = "".join(letter for field, letter in day_fields if field in request.POST)

    # 5. Save it
    Course.objects.create(
        name=name,
        instructor=instructor,
        meeting_days=meeting_days,
        start_time=start_time,
        end_time=end_time,
    )

    return HttpResponse("Course created", status=200)

@csrf_exempt
def createLecture(request):
    # 1. Authorization first
    instructor = get_instructor(request.user)
    if instructor is None:
        return HttpResponse("Unauthorized", status=401)

    # 2. Only POST is allowed
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    # 3. Find the course by name
    course_name = request.POST.get("choice", "").strip()
    course = Course.objects.filter(name=course_name).first()
    if course is None:
        return HttpResponse("Course not found", status=400)

    # 4. Create the lecture for today (qr_identifier is generated automatically)
    Lecture.objects.create(course=course, date=timezone.localdate())

    return HttpResponse("Lecture created", status=200)

@csrf_exempt
def createQRCodeUpload(request):
    # 1. Authorization first, students only
    student = get_student(request.user)
    if student is None:
        return HttpResponse("Unauthorized", status=401)

    # 2. Only POST is allowed
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    # 3. Get the uploaded file (files are in request.FILES, not request.POST)
    image = request.FILES.get("imageUpload")
    if image is None:
        return HttpResponse("Missing imageUpload file", status=400)

    # 4. Save it (uploaded_at is set automatically; lecture stays empty for now)
    QRCodeUpload.objects.create(student=student, image=image)

    return HttpResponse("Upload received", status=200)

def dumpUploads(request):
    # 1. Authorization first, instructors only
    instructor = get_instructor(request.user)
    if instructor is None:
        return HttpResponse("Unauthorized", status=401)

    # 2. Only GET is allowed
    if request.method != "GET":
        return HttpResponse("Method not allowed", status=405)

    # 3. Build the list of dictionaries
    data = []
    for upload in QRCodeUpload.objects.select_related("student__user").all():
        data.append({
            "username": upload.student.user.username,
            "upload_time": timezone.localtime(upload.uploaded_at).strftime("%Y-%m-%d %H:%M:%S"),
        })

    # 4. Return it as JSON (safe=False because it's a list, not a dict)
    return JsonResponse(data, safe=False)

# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------




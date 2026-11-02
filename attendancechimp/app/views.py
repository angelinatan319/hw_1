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
import zoneinfo
import json
import io
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import InstructorProfile, StudentProfile


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



# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------




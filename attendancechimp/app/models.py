"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- CourseProfile   : extends Django User → instructor-specific data
- StudentProfile  : extends Django User → student-specific data
- Course          : a course taught by one instructor
- Enrollment      : junction table linking students to courses
- Lecture         : a single class meeting (has a QR-code identifier)
- QRCodeUpload    : a student's uploaded QR-code photograph
"""

from django.db import models
from django.contrib.auth.models import User

import logging
import string
import random

logger = logging.getLogger(__name__) # set up tracking, auditing, and debugging
                                                               # allows using logger.warning(), logger.error(), 
                                                               # logger.info(), etc. Better than print() for debuggin... 


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

class InstructorProfile(models.Model):
    """
    An instructor who teaches courses.

    Linked one-to-one to Django's built-in User, which handles login and
    passwords. Instructors and students are separate tables (rather than one
    Users table with a "role" column) because they store different data and
    play different roles: foreign keys can then guarantee that, e.g., only an
    instructor can own a Course and only a student can upload a QR code.

    Fields
    ------
    user  : the login account for this instructor (unique)
    name  : display name
    email : contact email
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name="instructor_profile")
    name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return self.name

class StudentProfile(models.Model):
    """
    A student who enrolls in courses and uploads QR codes as attendance.

    Linked one-to-one to Django's built-in User.

    Fields
    ------
    user  : the login account for this student (unique)
    name  : display name
    email : contact email
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name="student_profile")
    name = models.CharField(max_length=100)
    email = models.EmailField()

    def courses(self):
        """Return a queryset of all courses this student is enrolled in."""
        return Course.objects.filter(enrollment__student=self)

    def __str__(self):
        return self.name

# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

class Course(models.Model):
    """
    A course taught by one instructor (one instructor → many courses).

    Fields
    ------
    name         : course name, e.g. "DATA 136"
    instructor   : the InstructorProfile who teaches it
    meeting_days : letters for the days it meets, e.g. "MWF" or "TR"
                   (M, T, W, R = Thursday, F, S, U = Sunday)
    start_time   : when each meeting starts
    end_time     : when each meeting ends
    """
    DAY_LETTERS = "MTWRFSU"  # position matches Python's date.weekday()

    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.CASCADE,
                                   related_name="courses")
    meeting_days = models.CharField(max_length=7)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def meets_on(self, date):
        """Return True if this course meets on the given date."""
        return self.DAY_LETTERS[date.weekday()] in self.meeting_days

    def students(self):
        """Return a queryset of all students enrolled in this course."""
        return StudentProfile.objects.filter(enrollment__course=self)

    def __str__(self):
        return self.name

# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class Enrollment(models.Model):
    """
    Junction table linking a student to a course.

    Student ↔ Course is many-to-many (a student takes many courses, a course
    has many students). Each Enrollment row records one such pairing.
    A student can be enrolled in the same course only once.

    Fields
    ------
    student : the enrolled StudentProfile
    course  : the Course they are enrolled in
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "course"],
                                    name="unique_enrollment"),
        ]

    def __str__(self):
        return f"{self.student} in {self.course}"

# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

def generate_qr_identifier(length=12):
    """
    Return a random string of letters and digits to encode in a lecture's
    QR code. Used as the default for Lecture.qr_identifier.

    (Defined here, above Lecture, because the class refers to it.)
    """
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


class Lecture(models.Model):
    """
    A single class meeting of a course (one course → many lectures).

    Fields
    ------
    course        : the Course this lecture belongs to
    date          : the day the lecture took place
    qr_identifier : unique random string encoded in this lecture's QR code,
                    generated automatically when the lecture is created
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE,
                               related_name="lectures")
    date = models.DateField()
    qr_identifier = models.CharField(max_length=64, unique=True,
                                     default=generate_qr_identifier)

    def attendees(self):
        """Return a queryset of students with an upload matched to this lecture."""
        return StudentProfile.objects.filter(qrcodeupload__lecture=self).distinct()

    def __str__(self):
        return f"{self.course} on {self.date}"

# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------

class QRCodeUpload(models.Model):
    """
    A photograph of a QR code uploaded by a student as proof of attendance.

    Fields
    ------
    student     : the StudentProfile who uploaded it
    lecture     : the Lecture the QR code matched. Optional (null) because an
                  upload may not match any lecture, e.g. before it has been
                  decoded or if the code is invalid. If the lecture is
                  deleted, the upload is kept and this is set to null.
    image       : the uploaded photo
    uploaded_at : timestamp, set automatically on creation
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, on_delete=models.SET_NULL,
                                null=True, blank=True)
    image = models.FileField(upload_to="qr_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload by {self.student} at {self.uploaded_at}"

# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------

def get_lecture_by_qr(qr_identifier):
    """Return the Lecture with this QR identifier, or None if there isn't one."""
    return Lecture.objects.filter(qr_identifier=qr_identifier).first()

def record_upload(student, image, qr_identifier=None):
    """
    Save a student's QR-code upload and match it to a lecture if possible.

    Parameters
    ----------
    student       : StudentProfile making the upload
    image         : the uploaded image file
    qr_identifier : the decoded QR string, or None if not decoded yet

    Returns the new QRCodeUpload. Its .lecture is None if no match was found.
    """
    lecture = get_lecture_by_qr(qr_identifier) if qr_identifier else None
    if qr_identifier and lecture is None:
        logger.warning("No lecture matches QR identifier %s", qr_identifier)
    upload = QRCodeUpload.objects.create(student=student, image=image,
                                         lecture=lecture)
    logger.info("Recorded upload %s (lecture=%s)", upload.id, lecture)
    return upload

def is_enrolled(student, course):
    """Return True if the student is enrolled in the course."""
    return Enrollment.objects.filter(student=student, course=course).exists()
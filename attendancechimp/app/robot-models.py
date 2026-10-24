
"""
Models for AttendanceChimp, a QR-code-based attendance application.

Includes instructor and student profiles, courses, enrollments,
lectures, and QR code upload records.
"""

import uuid

from django.conf import settings
from django.db import models


### Made from ChatGPT
### Prompt:
# Write a Django models.py for an attendance app called AttendanceChimp. 
# It needs these tables: InstructorProfile and StudentProfile (each linked
# to Djangos User), Course (name, instructor, meeting schedule), Enrollment
# (links students to courses, many-to-many), Lecture (linked to a course,
# with a date and a unique QR identifier), and QRCodeUpload (linked to a
# student and optionally a lecture). Include docstrings.

class InstructorProfile(models.Model):
    """Stores instructor-specific information for a Django user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )

    def __str__(self):
        """Return the instructor's username."""
        return self.user.get_username()


class StudentProfile(models.Model):
    """Stores student-specific information for a Django user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    def __str__(self):
        """Return the student's username."""
        return self.user.get_username()


class Course(models.Model):
    """Represents a course taught by an instructor."""

    name = models.CharField(max_length=200)

    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    meeting_schedule = models.TextField(
        help_text="Describe the course meeting days and times."
    )

    students = models.ManyToManyField(
        StudentProfile,
        through="Enrollment",
        related_name="courses",
        blank=True,
    )

    def __str__(self):
        """Return the course name."""
        return self.name


class Enrollment(models.Model):
    """Links a student to a course and records enrollment details."""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Define enrollment constraints."""

        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]

    def __str__(self):
        """Return a readable enrollment description."""
        return f"{self.student} enrolled in {self.course}"


class Lecture(models.Model):
    """Represents a scheduled lecture with a unique QR identifier."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lectures",
    )

    date = models.DateField()

    qr_identifier = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique identifier associated with this lecture's QR code.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Define lecture ordering."""

        ordering = ["date"]

    def __str__(self):
        """Return the course and lecture date."""
        return f"{self.course.name} - {self.date}"


class QRCodeUpload(models.Model):
    """Records a QR-code upload submitted by a student."""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="qr_uploads",
    )

    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qr_uploads",
        help_text="The lecture associated with this upload, if identified.",
    )

    image = models.ImageField(
        upload_to="attendance_qr_uploads/",
        help_text="Uploaded QR-code image.",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return a readable description of the upload."""
        return f"QR upload by {self.student} at {self.uploaded_at}"


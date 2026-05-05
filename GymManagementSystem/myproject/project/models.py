from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    img = models.ImageField(upload_to='team_members/')
    twitter = models.URLField(max_length=200, blank=True, null=True)
    facebook = models.URLField(max_length=200, blank=True, null=True)
    instagram = models.URLField(max_length=200, blank=True, null=True)
    linkedin = models.URLField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Enquiry(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]

    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Enquiries"

    def __str__(self):
        return self.name


class Plan(models.Model):
    DURATION_CHOICES = [
        ('Monthly Plans', 'Monthly Plans'),
        ('Yearly Plans', 'Yearly Plans'),
    ]

    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50, choices=DURATION_CHOICES)
    duration_days = models.PositiveIntegerField(
        default=30,
        help_text="Length of the plan in days; used to compute expiry.",
    )

    def __str__(self):
        return f"{self.name} ({self.duration})"


class Equipment(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
    GOAL_CHOICES = [
        ('lose', 'Lose Weight'),
        ('gain', 'Gain Muscle'),
        ('maintain', 'Maintain'),
    ]
    EXPERIENCE_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    DIET_CHOICES = [
        ('veg', 'Vegetarian'),
        ('nonveg', 'Non-Vegetarian'),
        ('vegan', 'Vegan'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='member_profile',
    )
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='members')
    join_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(blank=True, null=True)
    amount = models.PositiveIntegerField()

    height_cm = models.PositiveIntegerField(blank=True, null=True)
    weight_kg = models.PositiveIntegerField(blank=True, null=True)
    goal = models.CharField(max_length=10, choices=GOAL_CHOICES, blank=True)
    experience = models.CharField(max_length=15, choices=EXPERIENCE_CHOICES, blank=True)
    diet = models.CharField(max_length=10, choices=DIET_CHOICES, blank=True)

    def save(self, *args, **kwargs):
        if not self.expiry_date and self.plan_id and self.join_date:
            self.expiry_date = self.join_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return bool(self.expiry_date and self.expiry_date >= timezone.now().date())

    @property
    def days_remaining(self):
        if not self.expiry_date:
            return 0
        return max(0, (self.expiry_date - timezone.now().date()).days)

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return None

    def __str__(self):
        return self.name


class Subscription(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        if not self.end_date and self.plan_id:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.name} – {self.plan.name} ({self.start_date} → {self.end_date})"


class Payment(models.Model):
    MODE_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('card', 'Card'),
        ('online', 'Online'),
    ]
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name='payments',
        null=True, blank=True,
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='cash')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='paid')
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-paid_at']

    def __str__(self):
        return f"{self.member.name} – ₹{self.amount} ({self.status})"


class Attendance(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attendance')
    check_in = models.DateTimeField(default=timezone.now)
    check_out = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-check_in']

    def __str__(self):
        return f"{self.member.name} @ {self.check_in:%Y-%m-%d %H:%M}"


class WorkoutPlan(models.Model):
    """AI-generated 7-day workout split."""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='workout_plans')
    goal = models.CharField(max_length=20)
    content = models.JSONField(help_text="Structured workout plan from Gemini.")
    raw_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Workout for {self.member.name} ({self.created_at:%Y-%m-%d})"


class DietPlan(models.Model):
    """AI-generated diet plan."""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='diet_plans')
    goal = models.CharField(max_length=20)
    diet_type = models.CharField(max_length=10)
    content = models.JSONField(help_text="Structured diet plan from Gemini.")
    raw_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Diet for {self.member.name} ({self.created_at:%Y-%m-%d})"


class Image(models.Model):
    photo = models.ImageField(upload_to="myimage")
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image #{self.pk}"

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.signals import post_delete
import uuid



class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)  # место проведения
    cover = models.ImageField(upload_to='event_covers/', blank=True, null=True)  # обложка
    registration_deadline = models.DateTimeField(null=True, blank=True)  # крайний срок
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    controller_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return self.title


class ScheduleItem(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='schedule_items')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f"{self.title} ({self.event.title})"


class Material(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='materials')
    schedule_item = models.ForeignKey('ScheduleItem', on_delete=models.CASCADE, null=True, blank=True, related_name='materials')
    file = models.FileField(upload_to='materials/')
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.description or f"Материал для {self.event.title}"


class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    checked_in = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} — {self.event.title}"


class Feedback(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='feedbacks', null=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    activity = models.ForeignKey(ScheduleItem, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    rating = models.IntegerField(choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        if self.activity:
            return f"Отзыв на активность {self.activity.title}"
        return f"Отзыв на мероприятие {self.event.title}"



class Profile(models.Model):
    ROLE_CHOICES = (
        ('organizer', 'Организатор'),
        ('controller', 'Контролёр'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"Профиль: {self.user.username}"



class ControllerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Контролёр {self.user.username} на {self.event.title}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # если профиль уже есть, ничего не делаем
        Profile.objects.get_or_create(user=instance)


@receiver(post_delete, sender=User)
def delete_profile_with_user(sender, instance, **kwargs):
    try:
        instance.profile.delete()
    except Profile.DoesNotExist:
        pass

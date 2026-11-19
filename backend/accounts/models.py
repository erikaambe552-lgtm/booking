from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(models.TextChoices):
    CAMPER = "CAMPER", "Visitor / Camper"
    VENUE_OPERATOR = "VENUE_OPERATOR", "Beach Venue Operator"
    GUIDE = "GUIDE", "Mountain Tour Guide"
    ADMIN = "ADMIN", "System Administrator"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CAMPER)
    phone = models.CharField(max_length=20, blank=True)
    hometown = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN or self.user.is_staff


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        role = Role.ADMIN if instance.is_superuser else Role.CAMPER
        UserProfile.objects.create(user=instance, role=role)

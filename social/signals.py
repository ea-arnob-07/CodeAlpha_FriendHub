from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Follow, Notification, Profile


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, **kwargs):
    Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=Follow)
def notify_new_follower(sender, instance, created, **kwargs):
    if created and instance.follower_id != instance.following_id:
        Notification.objects.create(
            recipient=instance.following,
            actor=instance.follower,
            notification_type=Notification.Type.FOLLOW,
        )

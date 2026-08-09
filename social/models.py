from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse

from .validators import validate_image_upload


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True, validators=[validate_image_upload])
    cover_photo = models.ImageField(upload_to="covers/%Y/%m/", blank=True, validators=[validate_image_upload])
    bio = models.CharField(max_length=240, blank=True)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following_links")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower_links")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow_relationship"),
            models.CheckConstraint(condition=~Q(follower=F("following")), name="prevent_self_follow"),
        ]
        indexes = [models.Index(fields=["follower", "-created_at"])]

    def clean(self):
        if self.follower_id == self.following_id:
            raise ValidationError("You cannot follow yourself.")

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField(max_length=2000, blank=True)
    image = models.ImageField(upload_to="posts/%Y/%m/", blank=True, validators=[validate_image_upload])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["author", "-created_at"])]

    def clean(self):
        if not self.content.strip() and not self.image:
            raise ValidationError("A post needs text or an image.")

    @property
    def is_edited(self):
        return (self.updated_at - self.created_at).total_seconds() > 2

    def get_absolute_url(self):
        return reverse("social:post_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"Post {self.pk} by {self.author.username}"


class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_post_like")]

    def __str__(self):
        return f"{self.user} likes post {self.post_id}"


class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    content = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "created_at"])]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post_id}"


class Notification(models.Model):
    class Type(models.TextChoices):
        FOLLOW = "follow", "New follower"
        LIKE = "like", "Post liked"
        COMMENT = "comment", "New comment"

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_notifications")
    notification_type = models.CharField(max_length=12, choices=Type.choices)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]

    @property
    def message(self):
        name = self.actor.get_full_name() or self.actor.username
        messages = {
            self.Type.FOLLOW: f"{name} started following you.",
            self.Type.LIKE: f"{name} liked your post.",
            self.Type.COMMENT: f"{name} commented on your post.",
        }
        return messages[self.notification_type]

    @property
    def target_url(self):
        if self.post_id:
            return self.post.get_absolute_url()
        return reverse("social:profile", kwargs={"username": self.actor.username})

    def __str__(self):
        return self.message

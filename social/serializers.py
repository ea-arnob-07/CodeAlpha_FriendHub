from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Comment, Follow, Notification, Post, PostLike, Profile


class RegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    terms = serializers.BooleanField()

    def validate_username(self, value):
        value = value.strip().lower()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("That username is already taken.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account already uses this email address.")
        return value

    def validate_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms to continue.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        validated_data.pop("terms")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    remember_me = serializers.BooleanField(default=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(request=request, username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        attrs["user"] = user
        return attrs


class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    bio = serializers.CharField(source="profile.bio", read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "full_name", "avatar_url", "bio", "is_following")

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_avatar_url(self, obj):
        if obj.profile.avatar:
            return obj.profile.avatar.url
        return ""

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or request.user == obj:
            return False
        prefetched = getattr(request, "following_user_ids", None)
        if prefetched is not None:
            return obj.id in prefetched
        return Follow.objects.filter(follower=request.user, following=obj).exists()


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", required=False)
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    post_count = serializers.IntegerField(source="user.posts.count", read_only=True)
    follower_count = serializers.IntegerField(source="user.follower_links.count", read_only=True)
    following_count = serializers.IntegerField(source="user.following_links.count", read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "username", "first_name", "last_name", "email", "full_name", "avatar", "avatar_url",
            "cover_photo", "cover_url", "bio", "location", "website", "created_at", "post_count",
            "follower_count", "following_count", "is_following",
        )
        extra_kwargs = {"avatar": {"write_only": True}, "cover_photo": {"write_only": True}}

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else ""

    def get_cover_url(self, obj):
        return obj.cover_photo.url if obj.cover_photo else ""

    def get_is_following(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user != obj.user
            and Follow.objects.filter(follower=request.user, following=obj.user).exists()
        )

    def validate_email(self, value):
        user = self.instance.user
        if User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account already uses this email address.")
        return value.lower()

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for field, value in user_data.items():
            setattr(instance.user, field, value.strip() if isinstance(value, str) else value)
        instance.user.save(update_fields=list(user_data.keys()))
        return super().update(instance, validated_data)


class CommentSerializer(serializers.ModelSerializer):
    author = UserMiniSerializer(read_only=True)
    can_delete = serializers.SerializerMethodField()
    created_display = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("id", "author", "content", "created_at", "created_display", "can_delete")
        read_only_fields = ("author",)

    def get_can_delete(self, obj):
        request = self.context.get("request")
        return bool(request and request.user == obj.author)

    def get_created_display(self, obj):
        from django.utils.timesince import timesince
        return f"{timesince(obj.created_at).split(',')[0]} ago"


class PostSerializer(serializers.ModelSerializer):
    author = UserMiniSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_edited = serializers.BooleanField(read_only=True)
    can_edit = serializers.SerializerMethodField()
    recent_comments = serializers.SerializerMethodField()
    created_display = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id", "author", "content", "image", "image_url", "created_at", "created_display",
            "updated_at", "is_edited", "like_count", "comment_count", "is_liked", "can_edit",
            "recent_comments",
        )
        read_only_fields = ("author",)
        extra_kwargs = {"image": {"write_only": True, "required": False}}

    def get_image_url(self, obj):
        return obj.image.url if obj.image else ""

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        liked_ids = getattr(request, "liked_post_ids", None)
        if liked_ids is not None:
            return obj.id in liked_ids
        return PostLike.objects.filter(user=request.user, post=obj).exists()

    def get_can_edit(self, obj):
        request = self.context.get("request")
        return bool(request and request.user == obj.author)

    def get_recent_comments(self, obj):
        comments = list(obj.comments.select_related("author", "author__profile").all())[-3:]
        return CommentSerializer(comments, many=True, context=self.context).data

    def get_created_display(self, obj):
        from django.utils.timesince import timesince
        return f"{timesince(obj.created_at).split(',')[0]} ago"

    def validate(self, attrs):
        content = attrs.get("content", getattr(self.instance, "content", ""))
        image = attrs.get("image", getattr(self.instance, "image", None))
        remove_image = self.context.get("remove_image", False)
        if remove_image:
            image = None
        if not str(content).strip() and not image:
            raise serializers.ValidationError("A post needs text or an image.")
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserMiniSerializer(read_only=True)
    message = serializers.CharField(read_only=True)
    target_url = serializers.CharField(read_only=True)
    created_display = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id", "actor", "notification_type", "message", "target_url", "is_read",
            "created_at", "created_display",
        )

    def get_created_display(self, obj):
        from django.utils.timesince import timesince
        return f"{timesince(obj.created_at).split(',')[0]} ago"


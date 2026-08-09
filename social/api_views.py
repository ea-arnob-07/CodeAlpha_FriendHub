from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Comment, Follow, Notification, Post, PostLike
from .serializers import (
    CommentSerializer,
    LoginSerializer,
    NotificationSerializer,
    PostSerializer,
    ProfileSerializer,
    RegistrationSerializer,
    UserMiniSerializer,
)


def ok(data=None, message="Success.", http_status=status.HTTP_200_OK, **extra):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return Response(payload, status=http_status)


def fail(message, errors=None, http_status=status.HTTP_400_BAD_REQUEST):
    payload = {"success": False, "message": message}
    if errors is not None:
        payload["errors"] = errors
    return Response(payload, status=http_status)


def parse_bool(value):
    return str(value).lower() in {"1", "true", "yes", "on"}


def optimized_posts():
    return Post.objects.select_related("author", "author__profile").prefetch_related(
        "likes", "comments__author", "comments__author__profile"
    )


def prepare_request_cache(request, posts=None):
    request.following_user_ids = set(
        Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    )
    if posts is not None:
        post_ids = [post.id for post in posts]
        request.liked_post_ids = set(
            PostLike.objects.filter(user=request.user, post_id__in=post_ids).values_list("post_id", flat=True)
        )


def paginate(queryset, request, per_page=10):
    paginator = Paginator(queryset, per_page)
    try:
        page_number = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page_number = 1
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        page = paginator.page(paginator.num_pages) if paginator.num_pages else []
    return page, {
        "page": getattr(page, "number", 1),
        "pages": paginator.num_pages,
        "count": paginator.count,
        "has_next": getattr(page, "has_next", lambda: False)(),
    }


@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def api_register(request):
    serializer = RegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return fail("Please correct the highlighted fields.", serializer.errors)
    user = serializer.save()
    login(request._request, user)
    return ok(
        UserMiniSerializer(user, context={"request": request}).data,
        "Your FriendHub account is ready!",
        status.HTTP_201_CREATED,
    )


@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return fail("Unable to sign in.", serializer.errors, status.HTTP_401_UNAUTHORIZED)
    user = serializer.validated_data["user"]
    login(request._request, user)
    if not serializer.validated_data["remember_me"]:
        request.session.set_expiry(0)
    return ok(UserMiniSerializer(user, context={"request": request}).data, "Welcome back to FriendHub!")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_logout(request):
    logout(request._request)
    return ok(message="You have been signed out safely.")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_me(request):
    return ok(ProfileSerializer(request.user.profile, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_feed(request):
    following_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    posts = optimized_posts().filter(Q(author=request.user) | Q(author_id__in=following_ids)).distinct()
    page, pagination = paginate(posts, request)
    page_posts = list(page)
    prepare_request_cache(request, page_posts)
    data = PostSerializer(page_posts, many=True, context={"request": request}).data
    return ok(data, "Feed loaded.", pagination=pagination)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def api_profile(request, username):
    user = get_object_or_404(User.objects.select_related("profile"), username__iexact=username)
    if request.method == "GET":
        return ok(ProfileSerializer(user.profile, context={"request": request}).data)
    if request.user != user:
        return fail("You can only edit your own profile.", http_status=status.HTTP_403_FORBIDDEN)
    serializer = ProfileSerializer(user.profile, data=request.data, partial=True, context={"request": request})
    if not serializer.is_valid():
        return fail("Please correct the profile fields.", serializer.errors)
    try:
        profile = serializer.save()
    except OSError:
        return fail("Image uploads are not supported in this demo environment.", http_status=status.HTTP_403_FORBIDDEN)
    if parse_bool(request.data.get("remove_avatar")):
        profile.avatar.delete(save=False)
        profile.avatar = ""
    if parse_bool(request.data.get("remove_cover")):
        profile.cover_photo.delete(save=False)
        profile.cover_photo = ""
    profile.save()
    return ok(ProfileSerializer(profile, context={"request": request}).data, "Profile updated.")


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def api_follow(request, user_id):
    target = get_object_or_404(User, pk=user_id, is_active=True)
    if target == request.user:
        return fail("You cannot follow yourself.")
    if request.method == "POST":
        try:
            with transaction.atomic():
                relationship, created = Follow.objects.get_or_create(follower=request.user, following=target)
                if created:
                    relationship.full_clean()
        except IntegrityError:
            created = False
        return ok(
            {"is_following": True, "follower_count": target.follower_links.count()},
            "You are now following this person." if created else "You already follow this person.",
            status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
    deleted, _ = Follow.objects.filter(follower=request.user, following=target).delete()
    return ok(
        {"is_following": False, "follower_count": target.follower_links.count()},
        "Unfollowed successfully." if deleted else "You were not following this person.",
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_connections(request, username, kind):
    user = get_object_or_404(User, username__iexact=username)
    if kind == "followers":
        users = User.objects.select_related("profile").filter(following_links__following=user)
    elif kind == "following":
        users = User.objects.select_related("profile").filter(follower_links__follower=user)
    else:
        return fail("Connection type must be followers or following.")
    page, pagination = paginate(users.order_by("username"), request, 20)
    prepare_request_cache(request)
    return ok(
        UserMiniSerializer(list(page), many=True, context={"request": request}).data,
        "Connections loaded.",
        pagination=pagination,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_posts(request):
    serializer = PostSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return fail("The post could not be published.", serializer.errors)
    try:
        post = serializer.save(author=request.user)
    except OSError:
        return fail("Image uploads are not supported in this demo environment.", http_status=status.HTTP_403_FORBIDDEN)
    
    prepare_request_cache(request, [post])
    return ok(
        PostSerializer(post, context={"request": request}).data,
        "Your post is now live.",
        status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def api_post_detail(request, post_id):
    post = get_object_or_404(optimized_posts(), pk=post_id)
    if request.method == "GET":
        prepare_request_cache(request, [post])
        return ok(PostSerializer(post, context={"request": request}).data)
    if request.user != post.author:
        return fail("You can only change your own posts.", http_status=status.HTTP_403_FORBIDDEN)
    if request.method == "DELETE":
        post.delete()
        return ok(message="Post deleted.")
    remove_image = parse_bool(request.data.get("remove_image"))
    serializer = PostSerializer(
        post,
        data=request.data,
        partial=True,
        context={"request": request, "remove_image": remove_image},
    )
    if not serializer.is_valid():
        return fail("The post could not be updated.", serializer.errors)
    if remove_image and post.image:
        post.image.delete(save=False)
        post.image = ""
    try:
        post = serializer.save()
    except OSError:
        return fail("Image uploads are not supported in this demo environment.", http_status=status.HTTP_403_FORBIDDEN)
    prepare_request_cache(request, [post])
    return ok(PostSerializer(post, context={"request": request}).data, "Post updated.")


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def api_like(request, post_id):
    post = get_object_or_404(Post.objects.select_related("author"), pk=post_id)
    if request.method == "POST":
        like, created = PostLike.objects.get_or_create(user=request.user, post=post)
        if created and post.author != request.user:
            Notification.objects.get_or_create(
                recipient=post.author,
                actor=request.user,
                notification_type=Notification.Type.LIKE,
                post=post,
            )
        return ok(
            {"is_liked": True, "like_count": post.likes.count()},
            "Post liked." if created else "You already like this post.",
        )
    deleted, _ = PostLike.objects.filter(user=request.user, post=post).delete()
    if deleted:
        Notification.objects.filter(
            recipient=post.author,
            actor=request.user,
            notification_type=Notification.Type.LIKE,
            post=post,
        ).delete()
    return ok({"is_liked": False, "like_count": post.likes.count()}, "Like removed.")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_comments(request, post_id):
    post = get_object_or_404(Post.objects.select_related("author"), pk=post_id)
    if request.method == "GET":
        comments = post.comments.select_related("author", "author__profile")
        page, pagination = paginate(comments, request, 20)
        return ok(
            CommentSerializer(list(page), many=True, context={"request": request}).data,
            "Comments loaded.",
            pagination=pagination,
        )
    serializer = CommentSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return fail("Comment could not be added.", serializer.errors)
    comment = serializer.save(author=request.user, post=post)
    if post.author != request.user:
        Notification.objects.create(
            recipient=post.author,
            actor=request.user,
            notification_type=Notification.Type.COMMENT,
            post=post,
        )
    return ok(
        CommentSerializer(comment, context={"request": request}).data,
        "Comment added.",
        status.HTTP_201_CREATED,
        comment_count=post.comments.count(),
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def api_comment_detail(request, comment_id):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=comment_id)
    if request.user != comment.author:
        return fail("You can only delete your own comments.", http_status=status.HTTP_403_FORBIDDEN)
    post = comment.post
    comment.delete()
    return ok({"comment_count": post.comments.count()}, "Comment deleted.")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_search(request):
    query = request.query_params.get("q", "").strip()[:100]
    if len(query) < 2:
        return ok([], "Type at least two characters.")
    users = User.objects.select_related("profile").filter(is_active=True).filter(
        Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
    ).order_by("username")[:8]
    prepare_request_cache(request)
    return ok(UserMiniSerializer(users, many=True, context={"request": request}).data, "Search complete.")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_notifications(request):
    notifications = request.user.notifications.select_related("actor", "actor__profile", "post")
    page, pagination = paginate(notifications, request, 20)
    return ok(
        NotificationSerializer(list(page), many=True, context={"request": request}).data,
        "Notifications loaded.",
        pagination=pagination,
        unread_count=request.user.notifications.filter(is_read=False).count(),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return ok(
        {"unread_count": request.user.notifications.filter(is_read=False).count()},
        "Notification marked as read.",
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_notifications_read_all(request):
    updated = request.user.notifications.filter(is_read=False).update(is_read=True)
    return ok({"updated": updated, "unread_count": 0}, "All notifications marked as read.")

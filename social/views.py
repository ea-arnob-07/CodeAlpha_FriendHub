from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.http import url_has_allowed_host_and_scheme
from functools import wraps

from .forms import ProfileUpdateForm, RegistrationForm, StyledAuthenticationForm, UserUpdateForm
from .models import Comment, Follow, Post, PostLike


def enriched_posts():
    return Post.objects.select_related("author", "author__profile").prefetch_related(
        "likes",
        Prefetch("comments", queryset=Comment.objects.select_related("author", "author__profile")),
    )


def attach_liked_ids(request, posts):
    ids = [post.id for post in posts]
    liked = set(PostLike.objects.filter(user=request.user, post_id__in=ids).values_list("post_id", flat=True))
    for post in posts:
        post.viewer_liked = post.id in liked
        post.preview_comments = list(post.comments.all())[-3:]


def guest_only(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("social:home")
        return view_func(request, *args, **kwargs)
    return wrapper


@guest_only
def login_view(request):
    form = StyledAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        if not form.cleaned_data.get("remember_me"):
            request.session.set_expiry(0)
        messages.success(request, "Welcome back to FriendHub!")
        next_url = request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect("social:home")
    return render(request, "auth/login.html", {"form": form})


@guest_only
def register_view(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your FriendHub account is ready!")
        return redirect("social:home")
    return render(request, "auth/register.html", {"form": form})


@login_required
def logout_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    messages.success(request, "You have been signed out safely.")
    return redirect("social:login")


@login_required
@ensure_csrf_cookie
def home(request):
    following_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    queryset = enriched_posts().filter(Q(author=request.user) | Q(author_id__in=following_ids)).distinct()
    page = Paginator(queryset, 10).get_page(request.GET.get("page", 1))
    attach_liked_ids(request, page.object_list)
    excluded = list(following_ids) + [request.user.id]
    suggestions = User.objects.select_related("profile").exclude(id__in=excluded).order_by("date_joined")[:5]
    return render(request, "home.html", {"page_obj": page, "suggestions": suggestions})


@login_required
@ensure_csrf_cookie
def profile_view(request, username):
    profile_user = get_object_or_404(User.objects.select_related("profile"), username__iexact=username)
    page = Paginator(enriched_posts().filter(author=profile_user), 10).get_page(request.GET.get("page", 1))
    attach_liked_ids(request, page.object_list)
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    tab = request.GET.get("tab", "posts")
    if tab not in {"posts", "followers", "following", "about"}:
        tab = "posts"
    followers = User.objects.select_related("profile").filter(
        following_links__following=profile_user
    ).order_by("username")
    following = User.objects.select_related("profile").filter(
        follower_links__follower=profile_user
    ).order_by("username")
    connection_page = None
    if tab == "followers":
        connection_page = Paginator(followers, 20).get_page(request.GET.get("page", 1))
    elif tab == "following":
        connection_page = Paginator(following, 20).get_page(request.GET.get("page", 1))
    return render(
        request,
        "profile.html",
        {
            "profile_user": profile_user,
            "page_obj": page,
            "is_following": is_following,
            "followers_preview": followers[:6],
            "following_preview": following[:6],
            "active_tab": tab,
            "connection_page": connection_page,
            "viewer_following_ids": set(
                Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
            ),
        },
    )


@login_required
@ensure_csrf_cookie
def post_detail(request, pk):
    post = get_object_or_404(enriched_posts(), pk=pk)
    attach_liked_ids(request, [post])
    return render(request, "post_detail.html", {"post": post})


@login_required
@ensure_csrf_cookie
def search_view(request):
    query = request.GET.get("q", "").strip()[:100]
    results = User.objects.none()
    if query:
        results = User.objects.select_related("profile").filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).order_by("username")
    page = Paginator(results, 12).get_page(request.GET.get("page", 1))
    following_ids = set(Follow.objects.filter(follower=request.user).values_list("following_id", flat=True))
    return render(request, "search.html", {"query": query, "page_obj": page, "following_ids": following_ids})


@login_required
@ensure_csrf_cookie
def notifications_view(request):
    notifications = request.user.notifications.select_related("actor", "actor__profile", "post")
    page = Paginator(notifications, 20).get_page(request.GET.get("page", 1))
    return render(request, "notifications.html", {"page_obj": page})


@login_required
def edit_profile(request):
    user_form = UserUpdateForm(request.POST or None, instance=request.user)
    profile_form = ProfileUpdateForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile = profile_form.save(commit=False)
        if profile_form.cleaned_data.get("remove_avatar"):
            profile.avatar.delete(save=False)
            profile.avatar = ""
        if profile_form.cleaned_data.get("remove_cover"):
            profile.cover_photo.delete(save=False)
            profile.cover_photo = ""
        profile.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("social:profile", username=request.user.username)
    return render(request, "edit_profile.html", {"user_form": user_form, "profile_form": profile_form})


def about(request):
    return render(request, "about.html")


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)

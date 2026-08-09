from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Comment, Follow, Notification, Post, PostLike, Profile


class FriendHubTestCase(TestCase):
    def setUp(self):
        self.ayesha = User.objects.create_user(
            username="ayesha", email="ayesha@example.test", password="SafePass123!", first_name="Ayesha"
        )
        self.nabil = User.objects.create_user(
            username="nabil", email="nabil@example.test", password="SafePass123!", first_name="Nabil"
        )
        self.samira = User.objects.create_user(
            username="samira", email="samira@example.test", password="SafePass123!", first_name="Samira"
        )
        self.client = APIClient()

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.ayesha)

    def test_profile_created_with_user(self):
        self.assertTrue(Profile.objects.filter(user=self.ayesha).exists())

    def test_home_redirects_anonymous_user(self):
        response = self.client.get(reverse("social:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("social:login"), response.url)

    def test_registration_api_creates_secure_account(self):
        payload = {
            "first_name": "Rafi",
            "last_name": "Ahmed",
            "username": "rafi",
            "email": "rafi@example.test",
            "password": "StrongNewPass123!",
            "password_confirm": "StrongNewPass123!",
            "terms": True,
        }
        response = self.client.post(reverse("social_api:register"), payload, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="rafi")
        self.assertTrue(user.check_password(payload["password"]))

    def test_login_api_rejects_bad_password(self):
        response = self.client.post(
            reverse("social_api:login"), {"username": "ayesha", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])

    def test_post_creation_requires_content_or_image(self):
        self.authenticate()
        response = self.client.post(reverse("social_api:posts"), {"content": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Post.objects.count(), 0)

    def test_post_create_edit_and_delete_by_owner(self):
        self.authenticate()
        created = self.client.post(reverse("social_api:posts"), {"content": "First moment"}, format="json")
        self.assertEqual(created.status_code, 201)
        post_id = created.data["data"]["id"]
        edited = self.client.patch(
            reverse("social_api:post-detail", args=[post_id]), {"content": "Updated moment"}, format="json"
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(Post.objects.get(pk=post_id).content, "Updated moment")
        deleted = self.client.delete(reverse("social_api:post-detail", args=[post_id]))
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(Post.objects.filter(pk=post_id).exists())

    def test_another_user_cannot_change_post(self):
        post = Post.objects.create(author=self.nabil, content="Protected post")
        self.authenticate(self.ayesha)
        response = self.client.patch(
            reverse("social_api:post-detail", args=[post.id]), {"content": "Taken over"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        post.refresh_from_db()
        self.assertEqual(post.content, "Protected post")

    def test_like_is_unique_and_creates_notification(self):
        post = Post.objects.create(author=self.nabil, content="Like this")
        self.authenticate(self.ayesha)
        url = reverse("social_api:like", args=[post.id])
        self.client.post(url)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PostLike.objects.filter(user=self.ayesha, post=post).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.nabil, notification_type="like").count(), 1)

    def test_comment_permissions_and_notification(self):
        post = Post.objects.create(author=self.nabil, content="Discuss this")
        self.authenticate(self.ayesha)
        created = self.client.post(
            reverse("social_api:comments", args=[post.id]), {"content": "Thoughtful reply"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        comment = Comment.objects.get()
        self.assertTrue(Notification.objects.filter(recipient=self.nabil, notification_type="comment").exists())
        self.authenticate(self.samira)
        denied = self.client.delete(reverse("social_api:comment-detail", args=[comment.id]))
        self.assertEqual(denied.status_code, 403)

    def test_follow_unfollow_and_self_follow_prevention(self):
        self.authenticate(self.ayesha)
        self_follow = self.client.post(reverse("social_api:follow", args=[self.ayesha.id]))
        self.assertEqual(self_follow.status_code, 400)
        url = reverse("social_api:follow", args=[self.nabil.id])
        followed = self.client.post(url)
        self.assertEqual(followed.status_code, 201)
        self.assertTrue(Follow.objects.filter(follower=self.ayesha, following=self.nabil).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.nabil, notification_type="follow").exists())
        unfollowed = self.client.delete(url)
        self.assertEqual(unfollowed.status_code, 200)
        self.assertFalse(Follow.objects.filter(follower=self.ayesha, following=self.nabil).exists())

    def test_database_rejects_duplicate_follow(self):
        Follow.objects.create(follower=self.ayesha, following=self.nabil)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Follow.objects.create(follower=self.ayesha, following=self.nabil)

    def test_personalized_feed_only_shows_self_and_followed_users(self):
        own = Post.objects.create(author=self.ayesha, content="Own")
        followed = Post.objects.create(author=self.nabil, content="Followed")
        hidden = Post.objects.create(author=self.samira, content="Hidden")
        Follow.objects.create(follower=self.ayesha, following=self.nabil)
        self.authenticate(self.ayesha)
        response = self.client.get(reverse("social_api:feed"))
        post_ids = {item["id"] for item in response.data["data"]}
        self.assertEqual(post_ids, {own.id, followed.id})
        self.assertNotIn(hidden.id, post_ids)

    def test_profile_can_only_be_updated_by_owner(self):
        self.authenticate(self.ayesha)
        denied = self.client.patch(
            reverse("social_api:profile", args=[self.nabil.username]), {"bio": "Changed"}, format="json"
        )
        self.assertEqual(denied.status_code, 403)
        updated = self.client.patch(
            reverse("social_api:profile", args=[self.ayesha.username]), {"bio": "My new bio"}, format="json"
        )
        self.assertEqual(updated.status_code, 200)
        self.ayesha.profile.refresh_from_db()
        self.assertEqual(self.ayesha.profile.bio, "My new bio")

    def test_search_finds_name_or_username(self):
        self.authenticate()
        response = self.client.get(reverse("social_api:search"), {"q": "Nabil"})
        usernames = {item["username"] for item in response.data["data"]}
        self.assertIn("nabil", usernames)

    def test_mark_all_notifications_read(self):
        Notification.objects.create(
            recipient=self.ayesha, actor=self.nabil, notification_type=Notification.Type.FOLLOW
        )
        self.authenticate()
        response = self.client.post(reverse("social_api:notifications-read-all"))
        self.assertEqual(response.data["data"]["unread_count"], 0)
        self.assertFalse(Notification.objects.filter(recipient=self.ayesha, is_read=False).exists())

    def test_credit_is_present_on_login_page(self):
        response = self.client.get(reverse("social:login"))
        self.assertContains(response, "Developed by Estiuk Arafat Arnob")

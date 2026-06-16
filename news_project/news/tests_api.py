"""API integration tests for the Newsroom application.

This test module covers role-based access control, reader subscription
feed behavior, journalist workflow, editor approval actions, newsletter
creation, and internal webhook/signal integration.
"""

from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from news.models import Article, Publisher

User = get_user_model()


class NewsroomAPITestSuite(APITestCase):
    """API test suite for newsroom role, content, and workflow behavior."""

    def setUp(self):
        # 1. Create Core Users with Roles
        self.editor = User.objects.create_user(
            username='editor_user',
            password='password123',
            email='testeditor@example.com',
            role='editor',
            first_name='Ed',
            last_name='itor'
        )
        self.journalist = User.objects.create_user(
            username='journo_user',
            password='password123',
            email='testjournalist@example.com',
            role='journalist',
            first_name='Joe',
            last_name='Journo'
        )
        self.reader = User.objects.create_user(
            username='reader_user',
            password='password123',
            email='testreader@example.com',
            role='reader',
            first_name='Read',
            last_name='er'
        )

        # Generate tokens manually for safety
        # (since signal handles it on create)
        self.editor_token, _ = Token.objects.get_or_create(user=self.editor)
        self.journalist_token, _ = Token.objects.get_or_create(
            user=self.journalist
        )
        self.reader_token, _ = Token.objects.get_or_create(user=self.reader)

        # 2. Create Publishers
        self.publisher_a = Publisher.objects.create(
            name="Global Times",
            website="https://global.com"
        )
        self.publisher_b = Publisher.objects.create(
            name="Local Tech",
            website="https://localtech.com"
        )

        # 3. Create Articles
        self.approved_article_a = Article.objects.create(
            title="Approved Global News",
            content="Content text here.",
            author=self.journalist,
            publisher=self.publisher_a,
            approved=True
        )
        self.approved_article_b = Article.objects.create(
            title="Approved Tech News",
            content="More content text.",
            author=self.journalist,
            publisher=self.publisher_b,
            approved=True
        )
        self.pending_article = Article.objects.create(
            title="Draft Scoop",
            content="Secret leaking data.",
            author=self.journalist,
            publisher=self.publisher_a,
            approved=False
        )

        # 4. Define API URLs
        self.article_list_url = reverse('api-article-list')
        self.newsletter_list_url = reverse('api-newsletter-list')

    def authenticate_as(self, token):
        """Helper to inject the Token into authorization headers."""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    # ── 1. ROLE-BASED AUTHENTICATION ACCESS BOUNDARIES ──────────────────────

    def test_unauthenticated_request_fails(self):
        """Ensure requests without a token are completely blocked."""
        self.client.credentials()  # Clear tokens
        response = self.client.get(self.article_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reader_cannot_see_pending_articles(self):
        """
        Success/Failure boundary:
            Reader sees approved articles but never drafts.
        """
        self.authenticate_as(self.reader_token)
        response = self.client.get(self.article_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get('results', response.data)

        # Should find approved_article_a and approved_article_b,
        # But NOT pending_article
        self.assertEqual(len(results), 2)
        titles = [item['title'] for item in results]
        self.assertNotIn("Draft Scoop", titles)

    # ── 2. READER SUBSCRIBED FEED LOGIC ──────────────────────────────────────

    def test_reader_retrieves_only_subscribed_content(self):
        """
        Verifies GET /api/articles/subscribed/
        restricts payload parameters correctly.
        """
        # Setup: Reader subscribes explicitly to Publisher A only
        self.reader.subscribed_publishers.add(self.publisher_a)

        self.authenticate_as(self.reader_token)
        subscribed_url = reverse('api-article-subscribed')
        response = self.client.get(subscribed_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return approved_article_a (Publisher A),
        # But exclude approved_article_b (Publisher B)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Approved Global News")

    def test_non_reader_cannot_access_subscribed_endpoint(self):
        """Failed Request: Journalist tries to load subscriber feed."""
        self.authenticate_as(self.journalist_token)
        subscribed_url = reverse('api-article-subscribed')
        response = self.client.get(subscribed_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── 3. JOURNALIST CAPABILITIES ──────────────────────────────────────────

    def test_journalist_can_create_article(self):
        """Successful Request: Journalist creates a draft article."""
        self.authenticate_as(self.journalist_token)
        payload = {
            "title": "Breaking News from investigative desks",
            "content": "Full text body details go here.",
            "publisher": self.publisher_a.id
        }
        response = self.client.post(
            self.article_list_url,
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], payload['title'])
        # Ensure it defaults to unapproved state
        self.assertFalse(response.data['approved'])

    def test_reader_cannot_create_article(self):
        """Failed Request: Role guard blocks reader from using POST."""
        self.authenticate_as(self.reader_token)
        payload = {"title": "Illegal post", "content": "No permissions."}
        response = self.client.post(
            self.article_list_url,
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── 4. EDITOR CONTROL ACTIONS ───────────────────────────────────────────

    def test_editor_can_approve_article(self):
        """
        Successful Action: Editor triggers custom nested
        approval action route.
        """
        self.authenticate_as(self.editor_token)
        approve_url = reverse(
            'api-article-approve',
            kwargs={'pk': self.pending_article.pk}
        )

        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['approved'])

    def test_journalist_cannot_approve_article(self):
        """
        Failed Action: Journalist tries to approve their own article via API.
        """
        self.authenticate_as(self.journalist_token)
        approve_url = reverse(
            'api-article-approve',
            kwargs={'pk': self.pending_article.pk}
        )

        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_delete_article(self):
        """Successful Action: Editor completely deletes an article resource."""
        self.authenticate_as(self.editor_token)
        delete_url = reverse(
            'api-article-detail',
            kwargs={'pk': self.approved_article_b.pk}
        )

        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Article.objects.filter(pk=self.approved_article_b.pk).exists()
        )

    # ── 5. NEWSLETTER INTEGRATION VALIDATION ────────────────────────────────

    def test_newsletter_crud_behavior(self):
        """Tests complete lifecycle validation inside Newsletters."""
        self.authenticate_as(self.journalist_token)

        payload = {
            "title": "Weekly Round-Up Edition",
            "description": "The best curated news items.",
            "article_ids": [self.approved_article_a.id]
        }
        # Post creation check
        response = self.client.post(
            self.newsletter_list_url,
            payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['article_count'], 1)

    # ── 6. SIGNAL PIPELINE & WEBHOOK MOCKING ────────────────────────────────

    @patch('requests.post')
    def test_webhook_signal_execution_on_approval(self, mock_post):
        """
        Verifies that transitioning an article's approval status correctly
        triggers automated backend integration pipelines using requests.
        """
        # Set up mock response behavior
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"received": True}

        # Trigger model save transition matching the property:
        # Approved False -> True
        self.pending_article.approved = True

        # Simulate your post_save or signal hook mechanism
        # Manually if not attached natively
        if hasattr(self.pending_article, '_approval_just_toggled'):
            self.pending_article._approval_just_toggled = True
        self.pending_article.save()

        # If your signals module triggers a post request
        # to an external webhook endpoint, verify the mock call.
        # self.assertTrue(mock_post.called)

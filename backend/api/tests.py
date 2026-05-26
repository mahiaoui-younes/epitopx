"""
EpitopX AI — Comprehensive test suite.
Covers: authentication, user management, proteins, epitopes,
        permissions, rate limiting, and security.

Run with:  python manage.py test api.tests --verbosity=2
"""
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import timedelta

from .models import (
    Protein, Epitope, Subscription,
    EmailVerificationToken, PasswordResetToken, AuditLog,
)
from .services import register_user, login_user, logout_user

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_user(username='testuser', email='test@example.com', password='StrongPass1!', is_admin=False):
    user = User.objects.create_user(username=username, email=email, password=password, is_admin=is_admin)
    Subscription.objects.get_or_create(user=user, defaults={'plan': 'free', 'status': 'active'})
    return user


def auth_client(user):
    """Return an APIClient authenticated as `user` via force_authenticate."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ─────────────────────────────────────────────────────────────────────────────
# Model Tests
# ─────────────────────────────────────────────────────────────────────────────

class UserModelTest(TestCase):

    def test_email_is_unique(self):
        make_user(username='u1', email='unique@example.com')
        with self.assertRaises(Exception):
            make_user(username='u2', email='unique@example.com')

    def test_default_is_email_verified_false(self):
        user = make_user()
        self.assertFalse(user.is_email_verified)

    def test_user_str(self):
        user = make_user()
        self.assertEqual(str(user), 'testuser')


class SubscriptionModelTest(TestCase):

    def test_free_plan_limits(self):
        user = make_user()
        sub = user.subscription
        self.assertEqual(sub.get_limit('proteins'), 10)
        self.assertEqual(sub.get_limit('analyses_month'), 20)

    def test_pro_plan_limits(self):
        user = make_user()
        sub = user.subscription
        sub.plan = 'pro'
        sub.save()
        self.assertEqual(sub.get_limit('proteins'), 100)

    def test_is_active(self):
        user = make_user()
        sub = user.subscription
        self.assertTrue(sub.is_active())
        sub.status = 'cancelled'
        sub.save()
        self.assertFalse(sub.is_active())


class PasswordResetTokenModelTest(TestCase):

    def test_valid_token(self):
        user = make_user()
        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.assertTrue(token.is_valid())

    def test_expired_token(self):
        user = make_user()
        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(token.is_valid())

    def test_used_token(self):
        user = make_user()
        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(minutes=30),
            used=True,
        )
        self.assertFalse(token.is_valid())


# ─────────────────────────────────────────────────────────────────────────────
# Service Tests
# ─────────────────────────────────────────────────────────────────────────────

class RegisterUserServiceTest(TestCase):

    def test_successful_registration(self):
        result = register_user('newuser', 'new@example.com', 'StrongPass1!')
        self.assertIn('user', result)
        self.assertIn('token', result)
        self.assertEqual(result['user'].username, 'newuser')

    def test_creates_free_subscription(self):
        result = register_user('newsub', 'sub@example.com', 'StrongPass1!')
        sub = Subscription.objects.filter(user=result['user']).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.plan, 'free')

    def test_duplicate_username_raises(self):
        register_user('dupuser', 'dup@example.com', 'StrongPass1!')
        with self.assertRaises(ValueError):
            register_user('dupuser', 'dup2@example.com', 'StrongPass1!')

    def test_duplicate_email_raises(self):
        register_user('emailuser1', 'same@example.com', 'StrongPass1!')
        with self.assertRaises(ValueError):
            register_user('emailuser2', 'same@example.com', 'StrongPass1!')


class LoginUserServiceTest(TestCase):

    def setUp(self):
        self.user = make_user(username='loginuser', email='login@example.com', password='StrongPass1!')

    def test_successful_login(self):
        result = login_user('loginuser', 'StrongPass1!')
        self.assertIn('token', result)

    def test_wrong_password(self):
        with self.assertRaises(ValueError):
            login_user('loginuser', 'wrongpassword')

    def test_nonexistent_user(self):
        with self.assertRaises(ValueError):
            login_user('noone', 'pass')

    def test_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        with self.assertRaises(ValueError):
            login_user('loginuser', 'StrongPass1!')


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoint Tests — Authentication
# ─────────────────────────────────────────────────────────────────────────────

class RegisterAPITest(APITestCase):

    def test_register_returns_201(self):
        r = self.client.post('/api/users/register/', {
            'username': 'apiuser1',
            'email':    'apiuser1@example.com',
            'password': 'StrongPass1!',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', r.data)
        self.assertIn('user', r.data)

    def test_register_missing_fields(self):
        r = self.client.post('/api/users/register/', {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email(self):
        r = self.client.post('/api/users/register/', {
            'username': 'badmail',
            'email':    'not-an-email',
            'password': 'StrongPass1!',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        r = self.client.post('/api/users/register/', {
            'username': 'weakpwd',
            'email':    'weak@example.com',
            'password': '123',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        make_user(username='existing', email='existing@example.com')
        r = self.client.post('/api/users/register/', {
            'username': 'existing',
            'email':    'another@example.com',
            'password': 'StrongPass1!',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_no_exception_leakage(self):
        """Error responses must not expose internal Python exceptions."""
        r = self.client.post('/api/users/register/', {
            'username': 'x' * 200,
            'email':    'ok@example.com',
            'password': 'StrongPass1!',
        }, format='json')
        self.assertNotIn('Traceback', str(r.data))
        self.assertNotIn('Exception', str(r.data))


class LoginAPITest(APITestCase):

    def setUp(self):
        self.user = make_user(username='loginapi', email='loginapi@example.com', password='StrongPass1!')

    def test_login_returns_200(self):
        r = self.client.post('/api/users/login/', {
            'username': 'loginapi',
            'password': 'StrongPass1!',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('token', r.data)

    def test_login_wrong_password(self):
        r = self.client.post('/api/users/login/', {
            'username': 'loginapi',
            'password': 'wrong',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_response_has_no_password(self):
        r = self.client.post('/api/users/login/', {
            'username': 'loginapi',
            'password': 'StrongPass1!',
        }, format='json')
        self.assertNotIn('password', str(r.data))


class ProfileAPITest(APITestCase):

    def test_profile_requires_auth(self):
        r = self.client.get('/api/users/profile/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_profile(self):
        user = make_user(username='profiletest', email='profile@example.com')
        client = auth_client(user)
        r = client.get('/api/users/profile/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['username'], 'profiletest')
        self.assertIn('subscription', r.data)


class LogoutAPITest(APITestCase):

    def test_logout_invalidates_token(self):
        user = make_user(username='logouttest', email='logout@example.com')
        # Create a DRF auth token explicitly so we can check it's deleted
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.force_authenticate(user=user)
        r = client.post('/api/users/logout/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(key=token.key).exists())


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoint Tests — Proteins
# ─────────────────────────────────────────────────────────────────────────────

class ProteinAPITest(APITestCase):

    def setUp(self):
        self.user  = make_user(username='puser',  email='puser@example.com')
        self.admin = make_user(username='padmin', email='padmin@example.com', is_admin=True)
        self.client_user  = auth_client(self.user)
        self.client_admin = auth_client(self.admin)
        self.pub_protein = Protein.objects.create(
            name='PublicProtein', sequence='ACDEFGHIKLM',
            created_by=self.admin, is_public=True,
        )
        self.priv_protein = Protein.objects.create(
            name='PrivateProtein', sequence='MNPQRSTVWY',
            created_by=self.user, is_public=False,
        )

    def test_list_proteins_requires_auth(self):
        r = self.client.get('/api/proteins/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_public_and_own(self):
        r = self.client_user.get('/api/proteins/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in r.data['results']]
        self.assertIn(self.pub_protein.id, ids)
        self.assertIn(self.priv_protein.id, ids)

    def test_create_protein(self):
        r = self.client_user.post('/api/proteins/', {
            'name':     'NewProtein',
            'sequence': 'ACDEFGHIKLM',
            'method':   'core',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['created_by_username'], 'puser')

    def test_update_own_protein(self):
        r = self.client_user.patch(f'/api/proteins/{self.priv_protein.id}/', {
            'name': 'UpdatedName',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['name'], 'UpdatedName')

    def test_cannot_update_other_users_protein(self):
        other = make_user(username='otherp', email='otherp@example.com')
        client_other = auth_client(other)
        r = client_other.patch(f'/api/proteins/{self.priv_protein.id}/', {
            'name': 'Hack',
        }, format='json')
        self.assertIn(r.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_delete_own_protein(self):
        r = self.client_user.delete(f'/api/proteins/{self.priv_protein.id}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_sees_all(self):
        r = self.client_admin.get('/api/proteins/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in r.data['results']]
        self.assertIn(self.pub_protein.id, ids)
        self.assertIn(self.priv_protein.id, ids)

    def test_invalid_sequence_rejected(self):
        r = self.client_user.post('/api/proteins/', {
            'name':     'BadSeq',
            'sequence': 'ACDEFG1234',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# Security Tests
# ─────────────────────────────────────────────────────────────────────────────

class SecurityTest(APITestCase):

    def test_api_root_requires_auth(self):
        r = self.client.get('/api/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_error_response_has_uniform_shape(self):
        r = self.client.get('/api/proteins/')
        self.assertIn('error', r.data)
        self.assertIn('code',  r.data)

    def test_cannot_access_other_user_protein_details(self):
        owner = make_user(username='sec_owner', email='owner@sec.com')
        other = make_user(username='sec_other', email='other@sec.com')
        protein = Protein.objects.create(
            name='Secret', sequence='ACDEF',
            created_by=owner, is_public=False,
        )
        client_other = auth_client(other)
        r = client_other.get(f'/api/proteins/{protein.id}/')
        self.assertIn(r.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_password_not_in_user_serializer(self):
        user = make_user(username='nopwd', email='nopwd@example.com')
        client = auth_client(user)
        r = client.get('/api/users/profile/')
        self.assertNotIn('password', r.data)

    def test_sql_injection_attempt_in_search(self):
        user = make_user(username='sqli', email='sqli@example.com')
        client = auth_client(user)
        r = client.get("/api/proteins/?search='; DROP TABLE api_protein; --")
        self.assertNotEqual(r.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────────────────
# Pagination Tests
# ─────────────────────────────────────────────────────────────────────────────

class PaginationTest(APITestCase):

    def setUp(self):
        self.user = make_user(username='pager', email='pager@example.com', is_admin=True)
        self.client_ = auth_client(self.user)
        Protein.objects.bulk_create([
            Protein(name=f'P{i}', sequence='ACDEF', created_by=self.user, is_public=True)
            for i in range(25)
        ])

    def test_paginated_response_shape(self):
        r = self.client_.get('/api/proteins/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('count',    r.data)
        self.assertIn('next',     r.data)
        self.assertIn('previous', r.data)
        self.assertIn('results',  r.data)

    def test_page_size_respected(self):
        r = self.client_.get('/api/proteins/?page_size=5')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(r.data['results']), 5)


# ─────────────────────────────────────────────────────────────────────────────
# Password Reset Tests
# ─────────────────────────────────────────────────────────────────────────────

class PasswordResetAPITest(APITestCase):

    def setUp(self):
        self.user = make_user(username='resetuser', email='reset@example.com', password='OldPass1!')

    def test_reset_request_always_200(self):
        for email in ['reset@example.com', 'nonexistent@example.com']:
            r = self.client.post('/api/users/password_reset/', {'email': email}, format='json')
            self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_confirm_with_invalid_token(self):
        r = self.client.post('/api/users/password-reset-confirm/', {
            'token':    str(uuid.uuid4()),
            'password': 'NewStrongPass1!',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_with_valid_token(self):
        token = PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        r = self.client.post('/api/users/password-reset-confirm/', {
            'token':    str(token.token),
            'password': 'BrandNewPass1!',
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        token.refresh_from_db()
        self.assertTrue(token.used)


# ─────────────────────────────────────────────────────────────────────────────
# Email Verification Tests
# ─────────────────────────────────────────────────────────────────────────────

class EmailVerificationAPITest(APITestCase):

    def setUp(self):
        self.user = make_user(username='verifyuser', email='verify@example.com')

    def test_verify_with_invalid_token(self):
        r = self.client.post('/api/users/verify-email/', {'token': str(uuid.uuid4())}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_with_valid_token(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        r = self.client.post('/api/users/verify-email/', {'token': str(token.token)}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_verify_with_expired_token(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        r = self.client.post('/api/users/verify-email/', {'token': str(token.token)}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

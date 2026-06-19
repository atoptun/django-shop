import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.accounts.forms import RegistrationForm, ProfileForm, AddressForm
from .factories import UserFactory, ProfileFactory, AddressFactory

User = get_user_model()


# Enable Django DB for all tests in this file
pytestmark = pytest.mark.django_db


# --- User & Profile Model Tests ---

def test_user_creation():
    user = UserFactory(username="testuser", email="test@example.com")
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.check_password("password123") is True


def test_user_profile_signal_creation():
    # Signal should automatically create a profile when user is created
    user = UserFactory()
    assert hasattr(user, "profile")
    assert user.profile.phone == ""
    assert user.profile.city == ""
    assert user.profile.address == ""


def test_profile_factory_creation():
    profile = ProfileFactory(phone="+380990000000", city="Lviv")
    assert profile.phone == "+380990000000"
    assert profile.city == "Lviv"
    assert str(profile) == f"Profile of {profile.user.username}"


# --- Form Tests ---

def test_registration_form_valid():
    form_data = {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "password2": "securepassword123",
    }
    form = RegistrationForm(data=form_data)
    assert form.is_valid() is True
    user = form.save()
    assert user.email == "newuser@example.com"
    assert user.username == "newuser@example.com"
    assert user.check_password("securepassword123") is True


def test_registration_form_existing_email():
    UserFactory(email="existing@example.com", username="existing@example.com")
    form_data = {
        "email": "existing@example.com",
        "password": "securepassword123",
        "password2": "securepassword123",
    }
    form = RegistrationForm(data=form_data)
    assert form.is_valid() is False
    assert "email" in form.errors or "__all__" in form.errors


def test_registration_form_passwords_mismatch():
    form_data = {
        "email": "newuser@example.com",
        "password": "password1",
        "password2": "password_mismatch",
    }
    form = RegistrationForm(data=form_data)
    assert form.is_valid() is False
    assert "__all__" in form.errors


def test_profile_form_initial_data():
    user = UserFactory(first_name="Jane", last_name="Smith")
    form = ProfileForm(instance=user.profile)
    assert form.fields["email"].initial == user.email
    assert form.fields["first_name"].initial == "Jane"
    assert form.fields["last_name"].initial == "Smith"


def test_profile_form_save():
    user = UserFactory(first_name="Jane", last_name="Smith")
    form_data = {
        "first_name": "Mary",
        "last_name": "Johnson",
        "phone": "+380509876543",
        "city": "Odessa",
        "address": "Deribasivska 1",
    }
    form = ProfileForm(data=form_data, instance=user.profile)
    assert form.is_valid() is True
    profile = form.save()
    user.refresh_from_db()
    assert user.first_name == "Mary"
    assert user.last_name == "Johnson"
    assert profile.phone == "+380509876543"
    assert profile.city == "Odessa"
    assert profile.address == "Deribasivska 1"


def test_profile_form_invalid_phone():
    user = UserFactory()
    form_data = {
        "first_name": "Mary",
        "last_name": "Johnson",
        "phone": "invalid-phone-number",
        "city": "Odessa",
        "address": "Deribasivska 1",
    }
    form = ProfileForm(data=form_data, instance=user.profile)
    assert form.is_valid() is False
    assert "phone" in form.errors


# --- View Tests ---

def test_register_view_get(client):
    url = reverse("accounts:register")
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/register.html" in [t.name for t in response.templates]


def test_register_view_post(client):
    url = reverse("accounts:register")
    form_data = {
        "email": "registerview@example.com",
        "password": "viewpassword123",
        "password2": "viewpassword123",
    }
    response = client.post(url, form_data)
    assert response.status_code == 302
    assert response.url == reverse("products:list_home")
    
    # Check user was created and logged in
    user = User.objects.get(email="registerview@example.com")
    assert user.is_active is True
    
    # Verify success message
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) > 0
    assert str(messages[0]) == "Account created successfully!"


def test_profile_view_anonymous(client):
    url = reverse("accounts:profile")
    response = client.get(url)
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_profile_view_authenticated(client):
    user = UserFactory()
    client.force_login(user)
    url = reverse("accounts:profile")
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/profile.html" in [t.name for t in response.templates]


def test_order_history_view(client):
    user = UserFactory()
    client.force_login(user)
    url = reverse("accounts:order_history")
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/order_history.html" in [t.name for t in response.templates]


def test_address_list_view(client):
    user = UserFactory()
    client.force_login(user)
    url = reverse("accounts:address_list")
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/address_list.html" in [t.name for t in response.templates]


def test_profile_view_post(client):
    user = UserFactory(first_name="Original", last_name="Name")
    client.force_login(user)
    url = reverse("accounts:profile")
    form_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "phone": "+380991112233",
        "city": "Dnipro",
        "address": "Central Ave 5",
    }
    response = client.post(url, form_data)
    assert response.status_code == 302
    assert response.url == reverse("accounts:profile")
    
    user.refresh_from_db()
    assert user.first_name == "Updated"
    assert user.profile.phone == "+380991112233"


def test_login_view_get(client):
    url = reverse("accounts:login")
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/login.html" in [t.name for t in response.templates]


def test_login_view_post_success(client):
    # RegistrationForm sets username = email
    UserFactory(username="loginuser@example.com", email="loginuser@example.com", password="correctpass")
    url = reverse("accounts:login")
    response = client.post(url, {"username": "loginuser@example.com", "password": "correctpass"})
    assert response.status_code == 302
    assert response.url == "/"


def test_login_view_post_failure(client):
    UserFactory(username="loginuser@example.com", email="loginuser@example.com", password="correctpass")
    url = reverse("accounts:login")
    response = client.post(url, {"username": "loginuser@example.com", "password": "wrongpass"})
    assert response.status_code == 200  # Reloads form with error


def test_password_reset_view_get(client):
    url = reverse("accounts:password_reset")
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/password_reset_form.html" in [t.name for t in response.templates]


def test_password_reset_confirm_view_redirect(client):
    user = UserFactory()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    url = reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    
    # GET request to confirm token should redirect to the tokenless set-password view
    response = client.get(url)
    assert response.status_code == 302
    assert "set-password" in response.url


# --- Address Model, Form, and View Tests ---

def test_address_model_creation():
    address = AddressFactory(recipient_name="Alex Smith", city="Kharkiv")
    assert address.recipient_name == "Alex Smith"
    assert address.city == "Kharkiv"
    assert str(address) == "Alex Smith - Kharkiv, Khreshchatyk St, 1, apt 10"
    assert address.created_at is not None
    assert address.updated_at is not None


def test_address_default_exclusivity():
    user = UserFactory()
    addr1 = AddressFactory(profile=user.profile, is_default=True)
    addr2 = AddressFactory(profile=user.profile, is_default=True)
    
    # Reload from DB
    addr1.refresh_from_db()
    addr2.refresh_from_db()
    
    # Only the most recent default address should be default
    assert addr1.is_default is False
    assert addr2.is_default is True
    
    # Verify it does not affect other users' default addresses
    other_user = UserFactory()
    other_addr = AddressFactory(profile=other_user.profile, is_default=True)
    
    addr2.refresh_from_db()
    assert addr2.is_default is True
    assert other_addr.is_default is True


def test_address_form_valid():
    form_data = {
        "recipient_name": "Mary Jane",
        "phone": "+380501112233",
        "city": "Poltava",
        "address_line": "Sobornosti St, 10",
        "is_default": True,
    }
    form = AddressForm(data=form_data)
    assert form.is_valid() is True


def test_address_form_invalid_phone():
    form_data = {
        "recipient_name": "Mary Jane",
        "phone": "invalid-phone",
        "city": "Poltava",
        "address_line": "Sobornosti St, 10",
        "is_default": True,
    }
    form = AddressForm(data=form_data)
    assert form.is_valid() is False
    assert "phone" in form.errors


def test_address_create_view(client):
    user = UserFactory()
    client.force_login(user)
    
    url = reverse("accounts:address_add")
    form_data = {
        "recipient_name": "New Recipient",
        "phone": "+380998887766",
        "city": "Sumy",
        "address_line": "Shevchenka St, 2",
        "is_default": False,
    }
    
    response = client.post(url, form_data)
    assert response.status_code == 302
    assert response.url == reverse("accounts:address_list")
    
    # Check the address was created in DB and associated with user's profile
    assert user.profile.addresses.filter(recipient_name="New Recipient").exists() is True


def test_address_update_view(client):
    user = UserFactory()
    client.force_login(user)
    
    address = AddressFactory(profile=user.profile, recipient_name="Old Name")
    url = reverse("accounts:address_edit", kwargs={"pk": address.pk})
    
    # GET request
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/address_form.html" in [t.name for t in response.templates]
    
    # POST request
    form_data = {
        "recipient_name": "Updated Name",
        "phone": address.phone,
        "city": address.city,
        "address_line": address.address_line,
        "is_default": address.is_default,
    }
    response = client.post(url, form_data)
    assert response.status_code == 302
    
    address.refresh_from_db()
    assert address.recipient_name == "Updated Name"


def test_address_update_view_permission_denied(client):
    user = UserFactory()
    other_user = UserFactory()
    client.force_login(user)
    
    # Address belongs to other_user
    address = AddressFactory(profile=other_user.profile, recipient_name="Other User Address")
    url = reverse("accounts:address_edit", kwargs={"pk": address.pk})
    
    response = client.get(url)
    assert response.status_code == 404


def test_address_delete_view(client):
    user = UserFactory()
    client.force_login(user)
    
    address = AddressFactory(profile=user.profile)
    url = reverse("accounts:address_delete", kwargs={"pk": address.pk})
    
    # GET request (confirmation page)
    response = client.get(url)
    assert response.status_code == 200
    assert "accounts/address_confirm_delete.html" in [t.name for t in response.templates]
    
    # POST request (delete)
    response = client.post(url)
    assert response.status_code == 302
    assert response.url == reverse("accounts:address_list")
    
    # Address should be deleted
    assert user.profile.addresses.filter(pk=address.pk).exists() is False


def test_address_delete_view_permission_denied(client):
    user = UserFactory()
    other_user = UserFactory()
    client.force_login(user)
    
    # Address belongs to other_user
    address = AddressFactory(profile=other_user.profile)
    url = reverse("accounts:address_delete", kwargs={"pk": address.pk})
    
    response = client.post(url)
    assert response.status_code == 404



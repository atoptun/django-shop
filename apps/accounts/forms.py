from django import forms

from .models import Address, Profile, User


class RegistrationForm(forms.ModelForm):
    email = forms.EmailInput(attrs={"class": "Input", "placeholder": "john@example.com"})
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "Input", "placeholder": "Password"}),
        label="Password",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "Input", "placeholder": "Confirm Password"}),
        label="Confirm Password",
    )

    class Meta:
        model = User
        fields = ["email"]  # "username",
        widgets = {
            # "username": forms.TextInput(attrs={"class": "Input", "placeholder": "John"}),
            "email": forms.EmailInput(attrs={"class": "Input", "placeholder": "john@example.com"}),
        }

    def clean(self) -> dict:
        cleaned = super().clean() or {}
        email = cleaned.get("email")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")

        self.instance.username = email
        return cleaned

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    email = forms.CharField(
        max_length=150,
        disabled=True,
        widget=forms.TextInput(attrs={"class": "Input", "readonly": "readonly"}),
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "Input", "placeholder": "John"}),
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "Input", "placeholder": "Doe"}),
    )

    field_order = ["email", "first_name", "last_name", "phone"]

    class Meta:
        model = Profile
        fields = ["phone"]
        widgets = {
            "phone": forms.TextInput(attrs={
                "class": "Input",
                "placeholder": "+380991234567",
                "pattern": r"^\+?[1-9]\d{9,14}$",
                "title": "Please enter a valid international phone number (e.g. +380991234567)"
            }),
            # "city": forms.TextInput(attrs={"class": "Input", "placeholder": "Kyiv"}),
            # "address": forms.Textarea(
            #     attrs={"class": "Input", "rows": 3, "placeholder": "Post address"}
            # ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["email"].initial = self.instance.user.email
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)

        if profile.user:
            profile.user.first_name = self.cleaned_data["first_name"]
            profile.user.last_name = self.cleaned_data["last_name"]
            if commit:
                profile.user.save()

        if commit:
            profile.save()
        return profile


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["recipient_name", "phone", "city", "address_line", "is_default"]
        widgets = {
            "recipient_name": forms.TextInput(attrs={"class": "Input", "placeholder": "John Doe"}),
            "phone": forms.TextInput(attrs={
                "class": "Input",
                "placeholder": "+380991234567",
                "pattern": r"^\+?[1-9]\d{9,14}$",
                "title": "Please enter a valid international phone number (e.g. +380991234567)"
            }),
            "city": forms.TextInput(attrs={"class": "Input", "placeholder": "Kyiv"}),
            "address_line": forms.Textarea(
                attrs={"class": "Input", "rows": 3, "placeholder": "Khreshchatyk St, 1, apt 10"}
            ),
            "is_default": forms.CheckboxInput(attrs={"class": "Checkbox"}),
        }


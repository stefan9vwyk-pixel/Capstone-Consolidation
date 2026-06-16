"""Forms used by the accounts app.

This module provides Django form classes for registration, authentication,
and profile editing. It customizes widgets and field ordering for a
consistent Bootstrap-friendly UI.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class RegisterForm(UserCreationForm):
    """Form used to register a new user.

    Extends Django's `UserCreationForm` to collect first name, last name,
    email and role in addition to username and password fields.
    """

    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': 'First name', 'class': 'form-control'}
        )
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': 'Last name', 'class': 'form-control'}
        )
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={'placeholder': 'Email address', 'class': 'form-control'}
        )
    )
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = CustomUser
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'password1',
            'password2'
        )
        widgets = {
            'username': forms.TextInput(
                attrs={'placeholder': 'Username', 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        """Add Bootstrap styling and placeholders to password fields."""
        super().__init__(*args, **kwargs)
        for field_name in ('password1', 'password2'):
            self.fields[field_name].widget.attrs.update(
                {'class': 'form-control'}
            )
        # Set placeholders for the empty fields.
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password2'].widget.attrs['placeholder'] = (
            'Confirm password'
        )


class LoginForm(AuthenticationForm):
    """Authentication form with custom widget styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })


class ProfileForm(forms.ModelForm):
    """Edit form for a user's public profile fields."""

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'bio', 'avatar_url')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avatar_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
        }

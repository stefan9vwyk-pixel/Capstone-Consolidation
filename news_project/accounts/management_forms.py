from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class UserCreateForm(UserCreationForm):
    """Editors can create journalist or reader accounts."""
    ALLOWED_ROLES = [
        (
            'journalist',
            'Journalist — can create, edit, delete articles & newsletters'
        ),
        (
            'reader',
            'Reader — can only view approved articles and newsletters'
        ),
    ]

    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'First name'}
        )
    )
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Last name'}
        )
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }
        )
    )
    role = forms.ChoiceField(
        choices=ALLOWED_ROLES,
        widget=forms.RadioSelect(
            attrs={'class': 'role-radio'}
        )
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'role')
        widgets = {
            'username': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'username'}
            ),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if any user already owns this email address
            if CustomUser.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError(
                    'A user with that email already exists.'
                )
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('password1', 'password2'):
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password2'].widget.attrs['placeholder'] = (
            'Confirm password'
        )
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None


class UserEditForm(forms.ModelForm):
    """
    Editors can update any user's profile and role.
    Reader-specific M2M fields are shown only when role=reader.
    Journalist content fields are read-only reverse relations
    (shown in template).
    """

    ROLE_CHOICES_WITH_EDITOR = [
        ('reader', 'Reader — view only'),
        ('journalist', 'Journalist — create, edit, delete'),
        ('editor', 'Editor — full access including approvals'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES_WITH_EDITOR,
        widget=forms.Select(
            attrs={'class': 'form-select', 'id': 'id_role'}
        )
    )

    # Reader subscription fields
    subscribed_publishers = forms.ModelMultipleChoiceField(
        queryset=None,   # set in __init__ to avoid import issues
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'checkbox-list'}
        ),
        label='Subscribed Publishers',
        help_text='Publishers this reader follows.',
    )
    subscribed_journalists = forms.ModelMultipleChoiceField(
        queryset=None,   # set in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'checkbox-list'}
        ),
        label='Subscribed Journalists',
        help_text='Journalists this reader follows.',
    )

    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'email', 'role',
            'bio', 'avatar_url', 'is_active',
            'subscribed_publishers', 'subscribed_journalists',
        )
        widgets = {
            'first_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'last_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'email': forms.EmailInput(
                attrs={'class': 'form-control'}
            ),
            'bio': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'avatar_url': forms.URLInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'https://…'
                }
            ),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

    def clean_email(self):
        """
        Check if the email provided is in use,
        Ensures emails are unique.
        """
        email = self.cleaned_data.get('email')
        if email:
            # Look for other accounts using this email, excluding
            # the current instance being edited
            query = CustomUser.objects.filter(
                email__iexact=email
            )
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                raise forms.ValidationError(
                    'This email address is already in use by '
                    'another account.'
                )
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deferred imports to avoid circular import at module load
        from news.models import Publisher
        self.fields[
            'subscribed_publishers'
        ].queryset = Publisher.objects.order_by('name')
        self.fields[
            'subscribed_journalists'
        ].queryset = CustomUser.objects.filter(
            role='journalist'
        ).order_by('last_name', 'first_name')

    def save(self, commit=True):
        """
        Save new user.
        """
        user = super().save(commit=False)
        if commit:
            # triggers _assign_group + _clear_irrelevant_subscriptions
            user.save()
            # M2M must be saved after the instance is committed
            self._save_m2m()
            # If role is not reader, clear M2M so they stay None
            if user.role != 'reader':
                user.subscribed_publishers.clear()
                user.subscribed_journalists.clear()
        return user

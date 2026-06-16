"""Forms used by the news app.

This module contains ModelForm definitions for creating and approving
articles and for composing newsletters. Forms adapt their fields based on
the requesting user's role (reader/journalist/editor).
"""

from django import forms
from .models import Article, Newsletter, Publisher


class ArticleForm(forms.ModelForm):
    """Form for creating and editing `Article` instances.

    - Automatically hides the `approved` field for non-editors.
    - Restricts the `publisher` queryset based on the user's role so that
        journalists and editors only see publishers relevant to them.
    """

    class Meta:
        model = Article
        fields = ('title', 'content', 'publisher', 'approved')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Article headline...'
            }),

            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 12,
                'placeholder': 'Write your article content here...'
            }),

            'publisher': forms.Select(attrs={'class': 'form-select'}),

            'approved': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Only editors are allowed to set the approval flag.
        if user and not user.is_editor:
            self.fields.pop('approved', None)

        # Limit publisher choices to those associated with the user.
        if user:
            if user.is_journalist:
                # Journalists see publishers they belong to (as a journalist).
                self.fields['publisher'].queryset = Publisher.objects.filter(
                    journalists=user
                )
                self.fields['publisher'].empty_label = (
                    'Independent (no publisher)'
                )

            elif user.is_editor:
                # Editors see publishers they edit.
                self.fields['publisher'].queryset = Publisher.objects.filter(
                    editors=user
                )
                self.fields['publisher'].empty_label = (
                    'Independent (no publisher)'
                )

            else:
                # Other roles should not be able to select a publisher.
                self.fields['publisher'].queryset = Publisher.objects.none()

    def save(self, commit=True):
        """Set the article author to the requesting user when present.

        Saves the instance and returns it. If `commit` is False, the unsaved
        instance is returned (standard ModelForm behavior).
        """
        article = super().save(commit=False)
        if self.user:
            article.author = self.user
        if commit:
            article.save()
        return article


class ArticleApproveForm(forms.ModelForm):
    """Small form used to toggle approval status on an Article."""

    class Meta:
        model = Article
        fields = ('approved',)
        widgets = {
            'approved': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }


class NewsletterForm(forms.ModelForm):
    """Form for creating/editing `Newsletter` instances.

    The `articles` field lists approved articles that can be added to the
    newsletter via checkboxes.
    """

    articles = forms.ModelMultipleChoiceField(
        queryset=Article.objects.filter(approved=True),
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'article-checkbox-list'}
        ),
        required=False,
        label='Include Articles',
        help_text='Select approved articles to include in this newsletter.'
    )

    class Meta:
        model = Newsletter
        fields = ('title', 'description', 'articles')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Newsletter title...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': (
                    'Brief description of this newsletter edition...'
                )
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        is_edit = kwargs.pop('is_edit', False)

        super().__init__(*args, **kwargs)

        # When creating a new newsletter,
        # Set the author to the requesting user.
        if not is_edit and user and not self.instance.pk:
            self.instance.author = user

    def save(self, commit=True):
        newsletter = super().save(commit=False)

        if commit:
            newsletter.save()
            self.save_m2m()
        return newsletter
        # Note: `save_m2m()` must be called after the instance is saved to
        # persist M2M relationships (handled above when commit is True).


class PublisherForm(forms.ModelForm):
    """
    For for creating and editing Publishers
    """
    class Meta:
        model = Publisher
        fields = ['name', 'description', 'website', 'editors', 'journalists']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'editors': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'journalists': forms.SelectMultiple(
                attrs={'class': 'form-control'}
            ),
        }

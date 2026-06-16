from django.db import models


class Publisher(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    editors = models.ManyToManyField(
        'accounts.CustomUser', blank=True,
        related_name='editing_publishers',
        limit_choices_to={'role': 'editor'},
    )
    journalists = models.ManyToManyField(
        'accounts.CustomUser', blank=True,
        related_name='publishing_for',
        limit_choices_to={'role': 'journalist'},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def approved_articles_count(self):
        '''Returns the total number of approved articles for this Publisher.'''
        return self.articles.filter(approved=True).count()


class Article(models.Model):
    title = models.CharField(max_length=300)
    content = models.TextField()
    author = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.CASCADE,
        related_name='articles', limit_choices_to={'role': 'journalist'},
    )
    publisher = models.ForeignKey(
        Publisher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles',
    )
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache the original approved state so signals
        # Can detect a real transition
        self.__original_approved = self.approved

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update cache after save so repeated saves don't re-fire
        self.__original_approved = self.approved

    def __str__(self):
        return self.title

    def get_status_label(self):
        return 'Approved' if self.approved else 'Pending'

    def get_status_class(self):
        return 'badge--success' if self.approved else 'badge--warning'

    @property
    def word_count(self):
        return len(self.content.split())

    @property
    def was_just_approved(self):
        """
        True when approved has changed from False → True (pre-save state).
        """
        return self.approved and not self.__original_approved


class Newsletter(models.Model):
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    author = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.CASCADE,
        related_name='newsletters',
    )
    articles = models.ManyToManyField(
        Article,
        blank=True,
        related_name='newsletters'
    )
    publisher = models.ForeignKey(
        'Publisher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='newsletters'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

from django.contrib.auth.decorators import user_passes_test


def _is_editor(user):
    """
    Checks if a user has editor permissions via role,
    group, or staff status.
    """
    if not user.is_authenticated:
        return False

    return (
        getattr(user, 'role', '') == 'editor' or
        user.groups.filter(name='Editors').exists() or
        user.is_superuser
    )


# Protects function-based views from unauthorized access
editor_required = user_passes_test(_is_editor, login_url='login')

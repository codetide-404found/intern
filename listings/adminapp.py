from django.contrib.admin.apps import AdminConfig


class InternAdminConfig(AdminConfig):
    """Use our own admin site (attention box, login lockout) as Django's default admin."""

    default_site = 'listings.sites.InternAdminSite'

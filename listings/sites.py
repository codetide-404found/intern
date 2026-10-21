from datetime import timedelta

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone

from . import security
from .models import Internship


def attention_summary(today=None):
    """What you should look at when you open the admin."""
    today = today or timezone.localdate()
    live = Internship.objects.open()
    real_live = live.filter(is_sample=False).count()
    sample_live = live.filter(is_sample=True).count()
    messages = []
    if real_live == 0 and sample_live:
        messages.append('Only sample listings are live. Students are not seeing any real internships yet.')
    elif real_live == 0:
        messages.append('No internships are live. Students see an empty page until you add some.')
    expiring = list(
        live.filter(is_sample=False, deadline__isnull=False, deadline__lte=today + timedelta(days=7)).order_by('deadline')
    )
    return {'messages': messages, 'expiring': expiring}


class InternAdminSite(admin.AdminSite):
    site_header = 'Intern Accra admin'
    site_title = 'Intern Accra admin'
    index_title = 'Manage internships'
    index_template = 'admin/listings/index.html'

    def index(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), 'attention': attention_summary()}
        return super().index(request, extra_context)

    def login(self, request, extra_context=None):
        if request.method == 'POST' and security.is_locked(request, request.POST.get('username', '')):
            minutes = max(1, security.seconds_left(request, request.POST.get('username', '')) // 60 + 1)
            return HttpResponse(
                '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Too many attempts</title>'
                '<body style="font:16px/1.5 system-ui,sans-serif;max-width:32rem;margin:15vh auto;padding:0 1rem">'
                '<h1>Too many failed login attempts</h1>'
                f'<p>For safety, login is paused. Try again in about {minutes} minute{"s" if minutes != 1 else ""}.</p>',
                status=429, headers={'Retry-After': str(minutes * 60)},
            )
        return super().login(request, extra_context)

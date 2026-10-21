"""Security helpers: login lockout and security headers.

Login lockout. After too many failed admin logins from one place for one
username, further attempts are refused for a while, even with the right
password. This slows down password guessing. It is keyed by IP address AND
username, so a stranger cannot lock you out by guessing your username from
their own connection.

Security headers. Public pages get a strict Content-Security-Policy that only
allows this site's own scripts and styles (plus Google Fonts), which blocks most
cross-site scripting. The admin is exempt because Django's admin uses inline
code, but it is hidden from search engines.
"""

import logging
import time

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.dispatch import receiver

log = logging.getLogger('listings.security')


def client_ip(request):
    """The visitor's IP address.

    Behind a host's proxy (PythonAnywhere, Render, ...) the real address is the entry
    the proxy added, which is the last one in X-Forwarded-For. Taking the first entry
    would let an attacker pick any address they like. Set DJANGO_TRUSTED_PROXIES=0 if
    the site is reached directly with no proxy in front.
    """
    n = settings.TRUSTED_PROXY_COUNT
    parts = [p.strip() for p in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if p.strip()]
    if n > 0 and parts:
        return parts[-n] if len(parts) >= n else parts[0]
    return request.META.get('REMOTE_ADDR', '')


def _keys(request, username):
    ip = client_ip(request)
    user = (username or '').strip().lower()[:150]
    return f'lf:ip:{ip}', f'lf:ipu:{ip}|{user}'


def _state(key):
    value = cache.get(key)
    if not value or time.time() - value['t0'] >= settings.LOGIN_THROTTLE_WINDOW:
        return None
    return value


def _count(key):
    value = _state(key)
    return value['n'] if value else 0


def _add_failure(key):
    now = time.time()
    value = _state(key) or {'n': 0, 't0': now}
    value['n'] += 1
    cache.set(key, value, timeout=max(1, int(settings.LOGIN_THROTTLE_WINDOW - (now - value['t0']))))


def is_locked(request, username):
    ip_key, ipu_key = _keys(request, username)
    return _count(ipu_key) >= settings.LOGIN_THROTTLE_LIMIT or _count(ip_key) >= settings.LOGIN_THROTTLE_IP_LIMIT


def seconds_left(request, username):
    now = time.time()
    left = 0
    for key in _keys(request, username):
        value = _state(key)
        if value:
            left = max(left, int(settings.LOGIN_THROTTLE_WINDOW - (now - value['t0'])))
    return left


@receiver(user_login_failed)
def _on_failed_login(sender, credentials, request=None, **kwargs):
    if request is None:
        return
    username = credentials.get('username', '')
    for key in _keys(request, username):
        _add_failure(key)
    log.warning('Failed admin login for %r from %s', username[:60], client_ip(request))


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    if request is not None:
        cache.delete(_keys(request, user.get_username())[1])


CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/' + settings.ADMIN_URL):
            response.headers.setdefault('X-Robots-Tag', 'noindex, nofollow')
        elif not settings.DEBUG:
            # In debug mode Django's own error pages use inline styles, so the policy is skipped there.
            response.headers.setdefault('Content-Security-Policy', CSP)
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=()')
        return response

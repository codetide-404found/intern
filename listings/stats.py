"""Privacy-friendly visit counting, plus the numbers shown on the admin Stats page.

What is stored for each page view: the date, which page, a daily hash standing in for
the visitor, and any filter or search used. What is never stored: IP address, user agent,
cookies, names or emails. The hash is built from the IP address and browser string plus
a secret and today's date, so it cannot be reversed and it changes every day.
"""

import hashlib
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Min
from django.utils import timezone

from .models import Internship, PageView

log = logging.getLogger(__name__)

BOT_WORDS = re.compile(
    r'bot|crawl|spider|slurp|preview|fetch|monitor|uptime|curl|wget|python-requests|http-client|headless|whatsapp|telegram|facebookexternalhit',
    re.I,
)


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def visitor_hash(request, day):
    raw = f"{settings.SECRET_KEY}|{day.isoformat()}|{_client_ip(request)}|{request.META.get('HTTP_USER_AGENT', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def should_count(request):
    if request.method != 'GET':
        return False
    ua = request.META.get('HTTP_USER_AGENT', '')
    if not ua or BOT_WORDS.search(ua):
        return False
    # Respect "Do Not Track" and Global Privacy Control.
    if request.META.get('HTTP_DNT') == '1' or request.META.get('HTTP_SEC_GPC') == '1':
        return False
    # Do not count the people running the site.
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and user.is_staff:
        return False
    return True


def record(request, kind, internship=None, programme='', area='', pay='', search='', results=None):
    """Save one page view. Never raises: a stats problem must not break the page."""
    try:
        if not should_count(request):
            return
        day = timezone.localdate()
        PageView.objects.create(
            day=day, kind=kind, visitor=visitor_hash(request, day), internship=internship,
            programme=programme[:80], area=area[:80], pay=pay[:10],
            search=search.strip().lower()[:60], results=results,
        )
    except Exception:  # noqa: BLE001
        log.exception('Could not record page view')


# ---------- numbers for the admin Stats page ----------

def _period(qs, since):
    qs = qs.filter(day__gte=since)
    visits = qs.values('day', 'visitor').distinct().count()
    return {'views': qs.count(), 'visits': visits}


def summary(today=None):
    today = today or timezone.localdate()
    qs = PageView.objects.all()
    since_7, since_30 = today - timedelta(days=6), today - timedelta(days=29)

    # Daily series for the last 14 days, with missing days filled in as zero.
    start = today - timedelta(days=13)
    rows = {
        r['day']: r for r in qs.filter(day__gte=start).values('day').annotate(
            views=Count('id'), visitors=Count('visitor', distinct=True))
    }
    series = []
    for i in range(14):
        d = start + timedelta(days=i)
        r = rows.get(d, {})
        series.append({'day': d, 'views': r.get('views', 0), 'visitors': r.get('visitors', 0)})
    peak = max([s['visitors'] for s in series] + [1])
    for s in series:
        s['pct'] = round(100 * s['visitors'] / peak)

    last30 = qs.filter(day__gte=since_30)
    top_internships = list(
        last30.filter(kind=PageView.Kind.DETAIL, internship__isnull=False)
        .values('internship', 'internship__role', 'internship__company')
        .annotate(views=Count('id'), visits=Count('visitor', distinct=True))
        .order_by('-views')[:10]
    )
    filters = last30.filter(kind=PageView.Kind.LIST)
    top_programmes = list(filters.exclude(programme='').values('programme').annotate(n=Count('id')).order_by('-n')[:8])
    top_areas = list(filters.exclude(area='').values('area').annotate(n=Count('id')).order_by('-n')[:8])
    top_searches = list(
        filters.exclude(search='').values('search')
        .annotate(n=Count('id'), fewest=Min('results')).order_by('-n')[:10]
    )
    no_result_searches = list(
        filters.exclude(search='').filter(results=0).values('search')
        .annotate(n=Count('id')).order_by('-n')[:10]
    )
    first = qs.order_by('day').values_list('day', flat=True).first()
    return {
        'today': {'visitors': qs.filter(day=today).values('visitor').distinct().count(), 'views': qs.filter(day=today).count()},
        'last7': _period(qs, since_7),
        'last30': _period(qs, since_30),
        'all': {'views': qs.count(), 'visits': qs.values('day', 'visitor').distinct().count()},
        'since': first,
        'series': series,
        'top_internships': top_internships,
        'top_programmes': top_programmes,
        'top_areas': top_areas,
        'top_searches': top_searches,
        'no_result_searches': no_result_searches,
        'open_now': Internship.objects.open().count(),
    }

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from . import stats
from .models import Internship, PageView, Programme


def _contact():
    wa = ''.join(c for c in settings.CONTACT_WHATSAPP if c.isdigit())
    return {
        'whatsapp': wa,
        'whatsapp_display': '+' + wa if wa else '',
        'email': settings.CONTACT_EMAIL,
    }


def internship_list(request):
    open_now = Internship.objects.open()

    q = request.GET.get('q', '').strip()
    programme = request.GET.get('programme', '').strip()
    area = request.GET.get('area', '').strip()
    pay = request.GET.get('pay', '').strip()
    sort = request.GET.get('sort', 'close')

    qs = open_now.prefetch_related('programmes')
    if q:
        qs = qs.filter(
            Q(role__icontains=q) | Q(company__icontains=q) | Q(area__icontains=q)
            | Q(about__icontains=q) | Q(programmes__name__icontains=q)
        ).distinct()
    if programme:
        qs = qs.filter(programmes__name=programme)
    if area:
        qs = qs.filter(area=area)
    if pay in Internship.Pay.values:
        qs = qs.filter(pay=pay)
    qs = qs.order_by('-confirmed_on', 'deadline') if sort == 'new' else qs.order_by('deadline', 'company')
    # Listings with no deadline sort last when sorting by closing date.
    listings = list(qs)
    if sort != 'new':
        listings.sort(key=lambda i: (i.deadline is None, i.deadline or 0))

    context = {
        'listings': listings,
        'total_open': open_now.count(),
        'has_samples': any(i.is_sample for i in listings),
        'programmes': Programme.objects.filter(internships__in=open_now).distinct(),
        'areas': sorted(set(open_now.values_list('area', flat=True))),
        'pay_options': Internship.Pay.choices,
        'f': {'q': q, 'programme': programme, 'area': area, 'pay': pay, 'sort': sort},
        'filtered': any([q, programme, area, pay]),
        'contact': _contact(),
        'last_update': (open_now.order_by('-updated').values_list('updated', flat=True).first()),
    }
    stats.record(
        request, 'list', programme=programme if programme else '', area=area, pay=pay if pay in Internship.Pay.values else '',
        search=q, results=len(listings),
    )
    return render(request, 'listings/list.html', context)


def internship_detail(request, pk, slug=None):
    item = get_object_or_404(Internship.objects.prefetch_related('programmes'), pk=pk, published=True)
    if slug is None:
        return redirect(item, permanent=True)
    stats.record(request, 'detail', internship=item)
    return render(request, 'listings/detail.html', {
        'item': item,
        'closed': not item.is_open,
        'wa_text': (
            f'Hello, I saw the {item.role} internship at {item.company} '
            'on Intern Accra and would like to apply.'
        ),
        'email_subject': f'Internship application: {item.role}',
        'email_body': (
            'Hello,\n\n'
            f'I would like to apply for the {item.role} internship at {item.company}, '
            'which I found on Intern Accra.\n\n'
            'Name:\nProgramme and level:\nPhone:\n\n'
            'My CV is attached.\n\nThank you.'
        ),
        'contact': _contact(),
    })

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Internship, Programme


def make(role='Intern', company='Acme', days=10, programmes=('Accounting',), **kw):
    today = timezone.localdate()
    data = dict(role=role, company=company, area='Osu', pay='Paid', whatsapp='0244000000')
    data.update(kw)
    if days is not None:
        data.setdefault('deadline', today + timedelta(days=days))
    item = Internship.objects.create(**data)
    item.programmes.set([Programme.objects.get_or_create(name=p)[0] for p in programmes])
    return item


class VisibilityTests(TestCase):
    def test_expired_and_hidden_listings_are_not_shown(self):
        make(role='Open one')
        make(role='Expired one', days=-1)
        make(role='Hidden one', published=False)
        r = self.client.get(reverse('listings:list'))
        self.assertContains(r, 'Open one')
        self.assertNotContains(r, 'Expired one')
        self.assertNotContains(r, 'Hidden one')

    def test_deadline_today_is_still_open(self):
        make(role='Closes today', days=0)
        self.assertContains(self.client.get(reverse('listings:list')), 'Closes today')

    def test_no_deadline_stays_open(self):
        make(role='Rolling', days=None, deadline=None)
        self.assertContains(self.client.get(reverse('listings:list')), 'Rolling')


class FilterTests(TestCase):
    def setUp(self):
        make(role='Bank intern', company='Bank A', programmes=('Accounting',), pay='Paid', area='Airport City')
        make(role='Clinic intern', company='Clinic B', programmes=('Pharmacy',), pay='Unpaid', area='Madina')

    def get(self, **params):
        return self.client.get(reverse('listings:list'), params)

    def test_filter_by_programme(self):
        r = self.get(programme='Pharmacy')
        self.assertContains(r, 'Clinic intern')
        self.assertNotContains(r, 'Bank intern')

    def test_filter_by_area_and_pay(self):
        self.assertContains(self.get(area='Airport City'), 'Bank intern')
        self.assertNotContains(self.get(area='Airport City'), 'Clinic intern')
        self.assertContains(self.get(pay='Unpaid'), 'Clinic intern')
        self.assertNotContains(self.get(pay='Unpaid'), 'Bank intern')

    def test_search_matches_company_and_programme(self):
        self.assertContains(self.get(q='clinic b'), 'Clinic intern')
        self.assertNotContains(self.get(q='clinic b'), 'Bank intern')
        self.assertContains(self.get(q='accounting'), 'Bank intern')

    def test_no_match_shows_clear_filters(self):
        r = self.get(q='zzzz')
        self.assertContains(r, 'No internships match')


class WhatsAppOptionalTests(TestCase):
    def test_button_shown_when_number_present(self):
        item = make(whatsapp='0244 123 456')
        r = self.client.get(item.get_absolute_url())
        self.assertContains(r, 'Apply on WhatsApp')
        self.assertContains(r, 'https://wa.me/233244123456')

    def test_no_button_when_number_empty(self):
        item = make(whatsapp='', email='hr@example.com')
        r = self.client.get(item.get_absolute_url())
        self.assertNotContains(r, 'Apply on WhatsApp')
        self.assertNotContains(r, 'wa.me')
        self.assertContains(r, 'hr@example.com')

    def test_needs_some_way_to_apply(self):
        item = Internship(role='X', company='Y', area='Osu', whatsapp='', email='', how_to_apply='')
        with self.assertRaises(ValidationError):
            item.clean()
        item.how_to_apply = 'Walk in with your CV'
        item.clean()

    def test_bad_whatsapp_number_rejected(self):
        item = Internship(role='X', company='Y', area='Osu', whatsapp='123')
        with self.assertRaises(ValidationError):
            item.clean()


class DetailTests(TestCase):
    def test_detail_page_and_short_url_redirect(self):
        item = make(role='Data Analyst')
        self.assertEqual(self.client.get(item.get_absolute_url()).status_code, 200)
        r = self.client.get(reverse('listings:detail_short', args=[item.pk]))
        self.assertRedirects(r, item.get_absolute_url(), status_code=301)

    def test_hidden_listing_is_404(self):
        item = make(published=False)
        self.assertEqual(self.client.get(item.get_absolute_url()).status_code, 404)

    def test_expired_listing_page_says_closed(self):
        item = make(days=-2)
        r = self.client.get(item.get_absolute_url())
        self.assertContains(r, 'Closed')
        self.assertNotContains(r, 'Apply on WhatsApp')

    def test_private_contact_person_is_never_public(self):
        item = make(contact_person='Secret Person')
        self.assertNotContains(self.client.get(item.get_absolute_url()), 'Secret Person')
        self.assertNotContains(self.client.get(reverse('listings:list')), 'Secret Person')

    def test_html_in_fields_is_escaped(self):
        item = make(role='<script>alert(1)</script>')
        self.assertNotContains(self.client.get(item.get_absolute_url()), '<script>alert(1)</script>')


class AdminTests(TestCase):
    def test_admin_requires_login(self):
        r = self.client.get('/manage/listings/internship/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/manage/login/', r['Location'])

    def test_admin_add_form_loads_for_staff(self):
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'pw-12345-xyz')
        self.client.login(username='boss', password='pw-12345-xyz')
        self.assertEqual(self.client.get('/manage/listings/internship/add/').status_code, 200)
        self.assertEqual(self.client.get('/manage/listings/internship/').status_code, 200)

    def test_admin_save_without_whatsapp(self):
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'pw-12345-xyz')
        self.client.login(username='boss', password='pw-12345-xyz')
        prog = Programme.objects.create(name='Law')
        today = timezone.localdate()
        r = self.client.post('/manage/listings/internship/add/', {
            'role': 'Legal Intern', 'company': 'Firm', 'area': 'Ridge', 'mode': 'On-site',
            'programmes': [prog.pk], 'pay': 'Unpaid', 'deadline': (today + timedelta(days=9)).isoformat(),
            'how_to_apply': 'Walk in with your CV', 'whatsapp': '', 'email': '',
            'confirmed_on': today.isoformat(), 'published': 'on',
        })
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['adminform'].form.errors)
        item = Internship.objects.get(role='Legal Intern')
        self.assertFalse(item.whatsapp_digits)


BROWSER = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36'


class VisitCountingTests(TestCase):
    def visit(self, url=None, ua=BROWSER, ip='10.0.0.1', **extra):
        return self.client.get(url or reverse('listings:list'), HTTP_USER_AGENT=ua, REMOTE_ADDR=ip, **extra)

    def test_visit_is_counted_without_storing_personal_data(self):
        from .models import PageView
        self.visit(ip='41.66.1.2')
        pv = PageView.objects.get()
        self.assertEqual(pv.kind, 'list')
        self.assertEqual(len(pv.visitor), 32)
        stored = ' '.join(str(getattr(pv, f.name)) for f in PageView._meta.fields)
        self.assertNotIn('41.66.1.2', stored)
        self.assertNotIn('Mozilla', stored)

    def test_same_visitor_counts_once_per_day_in_visits(self):
        from .models import PageView
        from .stats import summary
        self.visit(); self.visit()
        self.visit(ip='10.0.0.2')
        s = summary()
        self.assertEqual(PageView.objects.count(), 3)
        self.assertEqual(s['today']['visitors'], 2)
        self.assertEqual(s['today']['views'], 3)

    def test_visitor_hash_changes_each_day(self):
        from datetime import date

        from django.test import RequestFactory

        from .stats import visitor_hash
        req = RequestFactory().get('/', HTTP_USER_AGENT=BROWSER, REMOTE_ADDR='10.0.0.1')
        self.assertNotEqual(visitor_hash(req, date(2026, 1, 1)), visitor_hash(req, date(2026, 1, 2)))
        self.assertEqual(visitor_hash(req, date(2026, 1, 1)), visitor_hash(req, date(2026, 1, 1)))

    def test_bots_previews_and_scripts_are_not_counted(self):
        from .models import PageView
        for ua in ['Googlebot/2.1', 'WhatsApp/2.23.1', 'curl/8.0', '']:
            self.visit(ua=ua)
        self.assertEqual(PageView.objects.count(), 0)

    def test_do_not_track_is_respected(self):
        from .models import PageView
        self.visit(HTTP_DNT='1')
        self.visit(HTTP_SEC_GPC='1')
        self.assertEqual(PageView.objects.count(), 0)

    def test_logged_in_staff_are_not_counted(self):
        from .models import PageView
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'pw-12345-xyz')
        self.client.login(username='boss', password='pw-12345-xyz')
        self.visit()
        self.assertEqual(PageView.objects.count(), 0)

    def test_detail_filters_and_searches_are_recorded(self):
        from .models import PageView
        item = make(role='Nurse aide', programmes=('Nursing',))
        self.visit(item.get_absolute_url())
        self.visit(reverse('listings:list') + '?programme=Nursing&area=Osu&q=Nurse')
        self.visit(reverse('listings:list') + '?q=Astronomy')
        detail = PageView.objects.get(kind='detail')
        self.assertEqual(detail.internship, item)
        filtered = PageView.objects.get(programme='Nursing')
        self.assertEqual((filtered.area, filtered.search, filtered.results), ('Osu', 'nurse', 1))
        self.assertEqual(PageView.objects.get(search='astronomy').results, 0)

    def test_hidden_listing_page_is_not_counted(self):
        from .models import PageView
        item = make(published=False)
        self.assertEqual(self.visit(item.get_absolute_url()).status_code, 404)
        self.assertEqual(PageView.objects.count(), 0)

    def test_page_still_works_if_counting_fails(self):
        from unittest import mock
        with mock.patch('listings.stats.PageView.objects.create', side_effect=RuntimeError('db down')):
            with self.assertLogs('listings.stats', level='ERROR'):
                self.assertEqual(self.visit().status_code, 200)


class StatsPageTests(TestCase):
    def test_stats_page_needs_login(self):
        r = self.client.get('/manage/listings/pageview/')
        self.assertEqual(r.status_code, 302)

    def test_stats_page_shows_numbers_and_missed_searches(self):
        make(role='Teller')
        for ip in ['10.0.0.1', '10.0.0.2']:
            self.client.get(reverse('listings:list') + '?q=astronomy', HTTP_USER_AGENT=BROWSER, REMOTE_ADDR=ip)
        item = Internship.objects.get()
        self.client.get(item.get_absolute_url(), HTTP_USER_AGENT=BROWSER, REMOTE_ADDR='10.0.0.1')
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'pw-12345-xyz')
        self.client.login(username='boss', password='pw-12345-xyz')
        r = self.client.get('/manage/listings/pageview/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['s']['today']['visitors'], 2)
        self.assertEqual(r.context['s']['today']['views'], 3)
        self.assertContains(r, 'astronomy')
        self.assertContains(r, 'Teller')

    def test_empty_stats_page_renders(self):
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'pw-12345-xyz')
        self.client.login(username='boss', password='pw-12345-xyz')
        r = self.client.get('/manage/listings/pageview/')
        self.assertContains(r, 'Nothing has been counted yet')

    def test_prune_command_removes_old_rows_only(self):
        from datetime import timedelta

        from django.core.management import call_command

        from .models import PageView
        today = timezone.localdate()
        PageView.objects.create(day=today - timedelta(days=500), kind='list', visitor='a')
        PageView.objects.create(day=today, kind='list', visitor='b')
        call_command('prune_stats', days=400)
        self.assertEqual(list(PageView.objects.values_list('visitor', flat=True)), ['b'])


class EmailApplyTests(TestCase):
    def test_email_and_whatsapp_both_shown_as_equal_options(self):
        item = make(whatsapp='0244 123 456', email='hr@example.com')
        r = self.client.get(item.get_absolute_url())
        self.assertContains(r, 'Apply on WhatsApp')
        self.assertContains(r, 'Apply by email')
        self.assertContains(r, 'Open in Gmail')
        self.assertContains(r, 'Copy address')

    def test_email_only_listing_has_no_whatsapp_button(self):
        item = make(whatsapp='', email='hr@example.com')
        r = self.client.get(item.get_absolute_url())
        self.assertContains(r, 'Apply by email')
        self.assertNotContains(r, 'Apply on WhatsApp')
        self.assertNotContains(r, 'wa.me')

    def test_whatsapp_only_listing_has_no_email_button(self):
        item = make(whatsapp='0244 123 456', email='')
        r = self.client.get(item.get_absolute_url())
        self.assertContains(r, 'Apply on WhatsApp')
        self.assertNotContains(r, 'Apply by email')
        self.assertNotContains(r, 'Open in Gmail')

    def test_mailto_is_prefilled_and_safely_encoded(self):
        item = make(role='Data & Research Intern', company='Acme', email='hr@example.com')
        html = self.client.get(item.get_absolute_url()).content.decode()
        self.assertIn('mailto:hr@example.com?subject=Internship%20application%3A%20Data%20%26%20Research%20Intern', html)
        self.assertIn('Acme', html)
        self.assertIn('https://mail.google.com/mail/?view=cm', html)
        self.assertIn('to=hr%40example.com', html)

    def test_cards_say_how_to_apply(self):
        make(role='Both', whatsapp='0244 123 456', email='a@example.com')
        make(role='Email only', whatsapp='', email='b@example.com')
        make(role='WA only', whatsapp='0244 123 456', email='')
        html = self.client.get(reverse('listings:list')).content.decode()
        self.assertIn('Apply by WhatsApp or email', html)
        self.assertIn('Apply by email', html)
        self.assertIn('Apply by WhatsApp', html)

    def test_closed_listing_shows_no_apply_buttons(self):
        item = make(days=-1, whatsapp='0244 123 456', email='a@example.com')
        r = self.client.get(item.get_absolute_url())
        self.assertNotContains(r, 'Apply by email')
        self.assertNotContains(r, 'Apply on WhatsApp')

    def test_admin_labels_email_field_for_applications(self):
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'pw-12345-xyz')
        self.client.login(username='boss', password='pw-12345-xyz')
        r = self.client.get('/manage/listings/internship/add/')
        self.assertContains(r, 'Email for applications')
        self.assertContains(r, 'Fill in WhatsApp, email, or both')


# ---------------- error pages, admin warning and security ----------------

import re as _re
from pathlib import Path as _Path
from unittest import mock as _mock

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.template.loader import render_to_string
from django.test import Client, override_settings


class ErrorPageTests(TestCase):
    def test_404_is_friendly_and_links_home(self):
        r = self.client.get('/no/such/page/')
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "We can&#x27;t find that page" if False else "find that page", status_code=404)
        self.assertContains(r, 'href="/"', status_code=404)

    def test_500_page_is_friendly_even_when_the_view_crashes(self):
        c = Client(raise_request_exception=False)
        with _mock.patch('listings.views.render', side_effect=RuntimeError('boom')):
            r = c.get(reverse('listings:list'))
        self.assertEqual(r.status_code, 500)
        self.assertContains(r, 'Something went wrong on our side', status_code=500)
        self.assertNotContains(r, 'boom', status_code=500)
        self.assertNotContains(r, 'Traceback', status_code=500)

    def test_error_pages_do_not_depend_on_anything_that_can_fail(self):
        root = _Path(__file__).parent / 'templates'
        for name in ['400.html', '403.html', '403_csrf.html', '404.html', '500.html']:
            text = (root / name).read_text()
            self.assertNotIn('{% extends', text, name)
            self.assertNotIn('{% static', text, name)
            self.assertNotIn('{% url', text, name)
            self.assertNotIn('{{', text, name)
            self.assertIn('<h1>', text, name)
            self.assertIn('href="/"', text, name)
            self.assertEqual(render_to_string(name).count('<h1>'), 1)

    def test_expired_listing_is_a_closed_page_not_an_error(self):
        item = make(days=-3)
        r = self.client.get(item.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Closed')


class AdminAttentionTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'pw-12345-xyz-long')
        self.client.login(username='boss', password='pw-12345-xyz-long')

    def test_warns_when_nothing_real_is_live(self):
        r = self.client.get('/manage/')
        self.assertContains(r, 'Needs attention')
        self.assertContains(r, 'No internships are live')

    def test_warns_when_only_samples_are_live(self):
        make(is_sample=True)
        self.assertContains(self.client.get('/manage/'), 'Only sample listings are live')

    def test_lists_real_listings_closing_within_a_week(self):
        make(role='Closing soon one', days=3)
        make(role='Far away one', days=40)
        r = self.client.get('/manage/')
        self.assertContains(r, 'close within 7 days')
        self.assertContains(r, 'Closing soon one')
        self.assertNotContains(r, 'Far away one')
        self.assertNotContains(r, 'No internships are live')

    def test_no_box_when_all_is_well(self):
        make(role='Healthy', days=40)
        self.assertNotContains(self.client.get('/manage/'), 'Needs attention')


class LoginLockoutTests(TestCase):
    def setUp(self):
        cache.clear()
        get_user_model().objects.create_superuser('boss', 'b@example.com', 'right-pass-12345')
        self.url = '/manage/login/'

    def attempt(self, password, ip='41.0.0.1', user='boss'):
        return self.client.post(
            self.url, {'username': user, 'password': password, 'next': '/manage/'}, HTTP_X_FORWARDED_FOR=ip,
        )

    def test_sixth_attempt_is_blocked_even_with_the_right_password(self):
        for _ in range(5):
            self.assertEqual(self.attempt('wrong').status_code, 200)
        r = self.attempt('right-pass-12345')
        self.assertEqual(r.status_code, 429)
        self.assertContains(r, 'Too many failed login attempts', status_code=429)
        self.assertIn('Retry-After', r)

    def test_other_places_are_not_locked_out(self):
        for _ in range(5):
            self.attempt('wrong', ip='41.0.0.1')
        r = self.attempt('right-pass-12345', ip='41.0.0.2')
        self.assertEqual(r.status_code, 302)

    def test_spoofed_first_forwarded_entry_does_not_dodge_the_lock(self):
        for i in range(5):
            self.attempt('wrong', ip=f'1.1.1.{i}, 41.0.0.1')   # attacker varies the first entry only
        r = self.attempt('right-pass-12345', ip='9.9.9.9, 41.0.0.1')
        self.assertEqual(r.status_code, 429)

    def test_good_login_clears_earlier_failures(self):
        for _ in range(3):
            self.attempt('wrong')
        self.assertEqual(self.attempt('right-pass-12345').status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.assertEqual(self.attempt('wrong').status_code, 200)

    def test_login_page_itself_always_opens(self):
        for _ in range(6):
            self.attempt('wrong')
        self.assertEqual(self.client.get(self.url).status_code, 200)


class SecurityHeaderTests(TestCase):
    def test_public_pages_have_a_strict_content_security_policy(self):
        r = self.client.get(reverse('listings:list'))
        csp = r['Content-Security-Policy']
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn('unsafe-inline', csp)
        self.assertNotIn('unsafe-eval', csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn('camera=()', r['Permissions-Policy'])
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_public_templates_have_no_inline_scripts_or_styles(self):
        # The policy above would block them, so make sure none are written.
        root = _Path(__file__).parent / 'templates' / 'listings'
        for path in root.glob('*.html'):
            text = path.read_text()
            self.assertIsNone(_re.search(r'<script(?![^>]*\bsrc=)[^>]*>', text), path.name)
            self.assertNotIn('<style', text, path.name)
            self.assertIsNone(_re.search(r'\sstyle=', text), path.name)
            self.assertIsNone(_re.search(r'\son(click|load|change|submit)=', text), path.name)

    def test_admin_is_hidden_from_search_engines(self):
        r = self.client.get('/manage/login/')
        self.assertIn('noindex', r['X-Robots-Tag'])

    def test_admin_url_must_be_logged_in_for_stats_and_data(self):
        for path in ['/manage/', '/manage/listings/internship/', '/manage/listings/pageview/']:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 302, path)
            self.assertIn('/manage/login/', r['Location'])

    def test_private_contact_person_is_not_shown_or_searchable(self):
        item = make(contact_person='Ama Secret', role='Visible role')
        self.assertNotContains(self.client.get(reverse('listings:list')), 'Ama Secret')
        self.assertNotContains(self.client.get(item.get_absolute_url()), 'Ama Secret')
        # Searching for the private name must not find the listing.
        found = self.client.get(reverse('listings:list'), {'q': 'Ama Secret'})
        self.assertNotContains(found, 'Visible role')
        self.assertContains(found, 'No internships match')

    def test_hostile_search_text_is_escaped_not_run(self):
        evil = '"><script>alert(1)</script>'
        r = self.client.get(reverse('listings:list'), {'q': evil})
        self.assertNotContains(r, '<script>alert(1)</script>')
        self.assertEqual(r.status_code, 200)

    def test_sql_special_characters_are_harmless(self):
        make(role='Safe')
        r = self.client.get(reverse('listings:list'), {'q': "x' OR 1=1; DROP TABLE listings_internship; --"})
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Safe')
        self.assertTrue(Internship.objects.filter(role='Safe').exists())

    def test_weak_admin_passwords_are_refused(self):
        for bad in ['short1', 'password1234', '12345678901234', 'internaccra']:
            with self.assertRaises(ValidationError):
                validate_password(bad)
        validate_password('river-lamp-orange-tractor-29')

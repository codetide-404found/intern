import re

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Programme(models.Model):
    """A course or field of study students can filter by, e.g. Accounting."""

    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class InternshipQuerySet(models.QuerySet):
    def open(self):
        """Published listings whose deadline has not passed."""
        today = timezone.localdate()
        return self.filter(published=True).filter(
            models.Q(deadline__isnull=True) | models.Q(deadline__gte=today)
        )


class Internship(models.Model):
    class Pay(models.TextChoices):
        PAID = 'Paid', 'Paid'
        STIPEND = 'Stipend', 'Stipend'
        UNPAID = 'Unpaid', 'Unpaid'

    class Mode(models.TextChoices):
        ONSITE = 'On-site', 'On-site'
        HYBRID = 'Hybrid', 'Hybrid'
        REMOTE = 'Remote', 'Remote'

    role = models.CharField('role title', max_length=120)
    company = models.CharField(max_length=120)
    area = models.CharField('area in Accra', max_length=80, help_text='For example Osu, Airport City or Madina.')
    mode = models.CharField('where', max_length=10, choices=Mode.choices, default=Mode.ONSITE)
    programmes = models.ManyToManyField(Programme, related_name='internships', help_text='Programmes the company accepts.')

    pay = models.CharField(max_length=10, choices=Pay.choices, default=Pay.STIPEND)
    pay_note = models.CharField('amount (optional)', max_length=80, blank=True, help_text='For example GHS 800 a month.')
    slots = models.PositiveSmallIntegerField('number of slots', null=True, blank=True)
    duration = models.CharField(max_length=40, blank=True, help_text='For example 3 months.')
    start_date = models.DateField('start date', null=True, blank=True)
    deadline = models.DateField(
        'application deadline', null=True, blank=True,
        help_text='The listing disappears from the site after this date. Leave empty only if the company has no deadline.',
    )

    about = models.TextField('about the role', blank=True)
    requirements = models.TextField('who can apply', blank=True, help_text='Level of study, skills, courses.')

    how_to_apply = models.CharField('how to apply', max_length=200, blank=True, help_text='For example: Send your CV and transcript.')
    whatsapp = models.CharField(
        'WhatsApp number', max_length=20, blank=True,
        help_text='Leave empty if this company does not use WhatsApp. Then no WhatsApp button is shown.',
    )
    email = models.EmailField('email', blank=True, help_text='Optional.')
    contact_person = models.CharField(
        'contact person (private)', max_length=120, blank=True,
        help_text='Who at the company confirmed this. Only you see this.',
    )

    confirmed_on = models.DateField(
        'confirmed with company on', default=timezone.localdate,
        help_text='The date a named person at the company confirmed this opening.',
    )
    published = models.BooleanField(default=True, help_text='Untick to hide the listing without deleting it.')
    is_sample = models.BooleanField('sample listing', default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = InternshipQuerySet.as_manager()

    class Meta:
        ordering = ['deadline', 'company']

    def __str__(self):
        return f'{self.role} at {self.company}'

    def get_absolute_url(self):
        return reverse('listings:detail', args=[self.pk, slugify(self.role) or 'internship'])

    @property
    def whatsapp_digits(self):
        """Number in international format with digits only, for wa.me links."""
        digits = re.sub(r'\D', '', self.whatsapp or '')
        if len(digits) == 10 and digits.startswith('0'):
            digits = '233' + digits[1:]
        return digits

    @property
    def whatsapp_display(self):
        return '+' + self.whatsapp_digits if self.whatsapp_digits else ''

    @property
    def days_left(self):
        if not self.deadline:
            return None
        return (self.deadline - timezone.localdate()).days

    @property
    def closing_soon(self):
        d = self.days_left
        return d is not None and 0 <= d <= 7

    @property
    def is_open(self):
        d = self.days_left
        return self.published and (d is None or d >= 0)

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.whatsapp:
            digits = self.whatsapp_digits
            if not 11 <= len(digits) <= 15:
                errors['whatsapp'] = 'Enter the full number, for example 0244 000 000.'
        if not self.whatsapp and not self.email and not self.how_to_apply:
            errors['how_to_apply'] = 'Add a way to apply: a WhatsApp number, an email, or instructions here.'
        if errors:
            raise ValidationError(errors)


class PageView(models.Model):
    """One visit to a public page. Used only for the admin Stats page.

    No names, emails, IP addresses or cookies are stored. The visitor value is a
    hash that changes every day, so a person cannot be followed from one day to the next.
    """

    class Kind(models.TextChoices):
        LIST = 'list', 'Home page'
        DETAIL = 'detail', 'Internship page'

    day = models.DateField(db_index=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    visitor = models.CharField(max_length=32)
    internship = models.ForeignKey(Internship, null=True, blank=True, on_delete=models.SET_NULL, related_name='views')
    programme = models.CharField(max_length=80, blank=True)
    area = models.CharField(max_length=80, blank=True)
    pay = models.CharField(max_length=10, blank=True)
    search = models.CharField(max_length=60, blank=True)
    results = models.PositiveIntegerField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'site stats'
        verbose_name_plural = 'site stats'
        indexes = [models.Index(fields=['day', 'kind'])]

    def __str__(self):
        return f'{self.day} {self.kind}'

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models import Internship, Programme

SAMPLES = [
    dict(role='Customer Service & Operations Intern', company='Sample Commercial Bank', area='Airport City',
         programmes=['Banking & Finance', 'Accounting', 'Business Administration'], pay='Stipend', pay_note='GHS 800 a month',
         mode='On-site', slots=4, duration='3 months', in_days=40, start_in=85,
         requirements='Level 300 or above. Comfortable with Excel. Final-year students preferred.',
         about='Rotate between branch operations and the back office. A supervisor is assigned from the first week.',
         whatsapp='0200000000', email='careers@example.com', how='Send your CV and latest transcript.'),
    dict(role='Data Analytics Intern', company='Sample Mobile Network', area='Airport City',
         programmes=['Computer Science / IT', 'Statistics', 'Mathematics'], pay='Paid', pay_note='GHS 1,500 a month',
         mode='Hybrid', slots=2, duration='6 months', in_days=48, start_in=78,
         requirements='Level 300 or above. Knows SQL or Python. Send a short note on a project you have done.',
         about='Work with the customer insights team on weekly reports and dashboards.',
         whatsapp='0200000000', email='careers@example.com', how='Email your CV with a link to any project.'),
    dict(role='Pharmacy Dispensing Intern', company='Sample Community Clinic', area='Madina',
         programmes=['Pharmacy', 'Nursing & Health'], pay='Unpaid', pay_note='',
         mode='On-site', slots=3, duration='2 months', in_days=6, start_in=15,
         requirements='Level 200 or above. Must be enrolled in a health programme.',
         about='Shadow the pharmacist on duty and learn stock control and patient counselling basics. A certificate is given at the end.',
         whatsapp='', email='', how='Come with your student ID and a printed CV. No WhatsApp: walk in at the clinic reception.'),
    dict(role='Content & Social Media Intern', company='Sample Radio & Digital', area='Osu',
         programmes=['Journalism & Media', 'Marketing', 'English'], pay='Stipend', pay_note='GHS 500 a month',
         mode='Hybrid', slots=5, duration='3 months', in_days=27, start_in=40,
         requirements='Any level. Bring two samples of your writing or video work.',
         about='Help plan and publish daily posts, write short scripts and cover live events around Accra.',
         whatsapp='0200000000', email='careers@example.com', how='Send samples of your work on WhatsApp.'),
    dict(role='Site Engineering Intern', company='Sample Engineering Works', area='Tema',
         programmes=['Civil Engineering', 'Electrical Engineering', 'Construction Technology'], pay='Paid', pay_note='GHS 1,000 a month',
         mode='On-site', slots=2, duration='4 months', in_days=55, start_in=92,
         requirements='Level 300 or above. Safety boots and helmet provided. Transport allowance not included.',
         about='Support site supervisors with measurements, progress logs and material checks on active projects.',
         whatsapp='', email='careers@example.com', how='Apply by email with your CV.'),
    dict(role='Programme Support Intern', company='Sample Community Foundation', area='Cantonments',
         programmes=['Social Work', 'Business Administration', 'Education'], pay='Stipend', pay_note='GHS 600 a month',
         mode='On-site', slots=2, duration='3 months', in_days=90, start_in=110,
         requirements='Level 300 or above. Good written English. Willing to travel to project sites.',
         about='Assist the programmes team with beneficiary records, event logistics and monthly reports.',
         whatsapp='0200000000', email='', how='Send your CV on WhatsApp.'),
]


class Command(BaseCommand):
    help = 'Add (or with --clear, remove) the sample listings used to show how the site works.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete all listings marked as samples.')

    def handle(self, *args, **opts):
        if opts['clear']:
            n, _ = Internship.objects.filter(is_sample=True).delete()
            self.stdout.write(f'Removed {n} sample listing(s).')
            return
        today = timezone.localdate()
        Internship.objects.filter(is_sample=True).delete()
        for s in SAMPLES:
            s = dict(s)
            progs = s.pop('programmes')
            in_days, start_in = s.pop('in_days'), s.pop('start_in')
            item = Internship.objects.create(
                deadline=today + timedelta(days=in_days), start_date=today + timedelta(days=start_in),
                how_to_apply=s.pop('how'), is_sample=True, **s,
            )
            item.programmes.set([Programme.objects.get_or_create(name=p)[0] for p in progs])
        self.stdout.write(f'Added {len(SAMPLES)} sample listings.')

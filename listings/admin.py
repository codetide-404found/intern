from django import forms
from django.contrib import admin
from django.template.response import TemplateResponse
from django.utils import timezone

from . import stats
from .models import Internship, PageView, Programme






class StatusFilter(admin.SimpleListFilter):
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [('open', 'Open now'), ('expired', 'Expired'), ('hidden', 'Hidden')]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == 'open':
            return queryset.open()
        if self.value() == 'expired':
            return queryset.filter(deadline__lt=today)
        if self.value() == 'hidden':
            return queryset.filter(published=False)
        return queryset


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    search_fields = ['name']


class InternshipForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = '__all__'
        labels = {'email': 'Email for applications'}
        help_texts = {
            'email': 'Leave empty if this company does not take applications by email. Then no email button is shown.',
        }


@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    form = InternshipForm
    list_display = ['role', 'company', 'area', 'pay', 'deadline', 'status', 'confirmed_on', 'is_sample']
    list_filter = [StatusFilter, 'pay', 'mode', 'area', 'is_sample']
    search_fields = ['role', 'company', 'area', 'contact_person']
    filter_horizontal = ['programmes']
    date_hierarchy = 'deadline'
    actions = ['hide', 'show']
    save_on_top = True

    fieldsets = [
        ('The role', {'fields': ['role', 'company', 'area', 'mode', 'programmes']}),
        ('Pay and timing', {'fields': ['pay', 'pay_note', 'slots', 'duration', 'start_date', 'deadline']}),
        ('Details', {'fields': ['about', 'requirements']}),
        ('How students apply', {
            'description': 'Fill in WhatsApp, email, or both. Each one you fill in becomes an Apply button on the listing. Leave one empty and its button is hidden. You can also just write instructions under "How to apply" (for example: walk in with your CV).',
            'fields': ['how_to_apply', 'whatsapp', 'email'],
        }),
        ('Your records', {'fields': ['contact_person', 'confirmed_on', 'published', 'is_sample']}),
    ]

    @admin.display(description='status')
    def status(self, obj):
        if not obj.published:
            return 'Hidden'
        return 'Open' if obj.is_open else 'Expired'

    @admin.action(description='Hide selected listings')
    def hide(self, request, queryset):
        self.message_user(request, f'{queryset.update(published=False)} listing(s) hidden.')

    @admin.action(description='Show selected listings')
    def show(self, request, queryset):
        self.message_user(request, f'{queryset.update(published=True)} listing(s) shown.')


@admin.register(PageView)
class SiteStatsAdmin(admin.ModelAdmin):
    """Shows the Stats page instead of a list of raw rows."""

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        context = {
            **self.admin_site.each_context(request),
            'title': 'Site stats',
            'opts': self.model._meta,
            's': stats.summary(),
        }
        return TemplateResponse(request, 'admin/listings/stats.html', context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

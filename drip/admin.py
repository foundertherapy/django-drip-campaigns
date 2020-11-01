import json

from django import forms
from django.contrib import admin
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.urls import path
from django.conf import settings

from drip.models import Drip, SentDrip, QuerySetRule, LimitedAccessDrip
from drip.drips import configured_message_classes, message_class_for
from drip.utils import get_user_model, get_simple_fields

CAN_ADD_DRIP = 'can_edit_drip_queryset'


class QuerySetRuleInline(admin.TabularInline):
    model = QuerySetRule


class DripForm(forms.ModelForm):
    message_class = forms.ChoiceField(
        choices=(
            (k, '{k} ({v})'.format(k=k, v=v))
            for k, v in configured_message_classes().items()
        ),
    )

    class Meta:
        model = Drip
        exclude = []


class DripAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled', 'message_class')
    inlines = [
        QuerySetRuleInline,
    ]
    form = DripForm
    users_fields = []
    actions = [
        'action_enable_drips',
        'action_disable_drips',
    ]

    def get_exclude(self, request, obj=None):
        languages = [val for val, label in settings.LANGUAGES]
        return [
            field.name[:field.name.rfind('_')] for field in Drip._meta.fields
            if any(field.name.endswith('_' + lang) for lang in languages)
        ]

    def get_model_perms(self, request):
        if not settings.ENABLE_QUERY_SET_RULE_PERMISSION:
            return super(DripAdmin, self).get_model_perms(request)

        if request.user.groups.filter(name='Drip Admin').exists():
            return super(DripAdmin, self).get_model_perms(request)
        else:
            return {}

    def action_enable_drips(self, request, queryset):
        queryset.update(enabled=True)
    action_enable_drips.short_description = 'Enable selected drips'

    def action_disable_drips(self, request, queryset):
        queryset.update(enabled=False)
    action_disable_drips.short_description = 'Disable selected drips'

    def av(self, view):
        return self.admin_site.admin_view(view)

    def timeline(self, request, drip_id, into_past, into_future):
        """
        Return a list of people who should get emails.
        """

        drip = get_object_or_404(Drip, id=drip_id)

        shifted_drips = []
        seen_users = set()
        for shifted_drip in drip.drip.walk(
            into_past=int(into_past), into_future=int(into_future)+1
        ):
            shifted_drip.prune()
            shifted_drips.append(
                {
                    'drip': shifted_drip,
                    'qs': shifted_drip.get_queryset().exclude(
                        id__in=seen_users,
                    ),
                },
            )
            seen_users.update(
                shifted_drip.get_queryset().values_list('id', flat=True)
            )

        return render(request, 'drip/timeline.html', locals())

    def get_mime_html_from_alternatives(self, alternatives):
        html = ''
        mime = ''
        for body, mime in alternatives:
            if mime == 'text/html':
                html = body
                mime = 'text/html'
        return html, mime

    def get_mime_html(self, drip, user):
        drip_message = message_class_for(
            drip.message_class,
        )(drip.drip, user)
        if drip_message.message.alternatives:
            return self.get_mime_html_from_alternatives(
                drip_message.message.alternatives
            )
        html = drip_message.message.body
        mime = 'text/plain'
        return html, mime

    def get_mime_html_for_sms(self, drip, user):
        drip_message = message_class_for(
            drip.message_class,
        )(drip.drip, user)
        html = drip_message.sms
        mime = 'text/plain'
        return html, mime

    def view_drip_email(
        self, request, drip_id, into_past, into_future, user_id
    ):

        drip = get_object_or_404(Drip, id=drip_id)
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)

        html, mime = self.get_mime_html(drip, user)

        return HttpResponse(html, content_type=mime)

    def view_drip_sms(
            self, request, drip_id, into_past, into_future, user_id
    ):
        drip = get_object_or_404(Drip, id=drip_id)
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        html, mime = self.get_mime_html_for_sms(drip, user)
        return HttpResponse(html, content_type=mime)

    def build_extra_context(self, extra_context):
        extra_context = extra_context or {}
        User = get_user_model()
        if not self.users_fields:
            self.users_fields = json.dumps(get_simple_fields(User))
        extra_context['field_data'] = self.users_fields
        return extra_context

    def add_view(self, request, extra_context=None):
        return super(DripAdmin, self).add_view(
            request, extra_context=self.build_extra_context(extra_context),
        )

    def change_view(self, request, object_id, extra_context=None):
        return super(DripAdmin, self).change_view(
            request,
            object_id,
            extra_context=self.build_extra_context(extra_context)
        )

    def get_urls(self):
        urls = super(DripAdmin, self).get_urls()
        my_urls = [
            path(
                '<int:drip_id>/timeline/<int:into_past>/<int:into_future>/',
                self.av(self.timeline),
                name='drip_timeline'
            ),
            path(
                '<int:drip_id>/timeline/<int:into_past>/'
                '<int:into_future>/<int:user_id>/email-view',
                self.av(self.view_drip_email),
                name='view_drip_email'
            ),
            path(
                '<int:drip_id>/timeline/<int:into_past>/'
                '<int:into_future>/<int:user_id>/sms-view',
                self.av(self.view_drip_sms),
                name='view_drip_sms'
            )
        ]
        return my_urls + urls


admin.site.register(Drip, DripAdmin)


class LimitedAccessDripAdmin(DripAdmin):
    def get_model_perms(self, request):
        if not settings.ENABLE_QUERY_SET_RULE_PERMISSION:
            return {}
        if request.user.groups.filter(name='Drip Admin').exists():
            return {}
        else:
            return super(DripAdmin, self).get_model_perms(request)

    change_form_template = 'admin/drip/change_form.html'
    inlines = []
    readonly_fields = ['is_queryset_added', 'message_class']

    def get_exclude(self, request, obj=None):
        excludes = super().get_exclude(request, obj)
        return excludes + ['from_email', 'from_email_name', ]

    def get_urls(self):
        return super(DripAdmin, self).get_urls()

    def is_queryset_added(self, obj):
        return obj.queryset_rules.count() > 0
    is_queryset_added.short_description = 'Are users conditions added'
    is_queryset_added.boolean = True


admin.site.register(LimitedAccessDrip, LimitedAccessDripAdmin)


class SentDripAdmin(admin.ModelAdmin):
    list_display = [f.name for f in SentDrip._meta.fields]
    ordering = ['-id']
    readonly_fields = [f.name for f in SentDrip._meta.fields]

    def has_add_permission(self, request):
        """
        SentDrip model is for details about the sent drip campaigns,
        its data shouldn't be changeable
        """
        return False


admin.site.register(SentDrip, SentDripAdmin)

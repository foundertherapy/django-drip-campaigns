import operator
import functools

from django.conf import settings
from django.db.models import Q
from django.template import Context, Template
from importlib import import_module
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from drip.models import SentDrip
from drip.utils import get_user_model
from drip.signals import post_drip

try:
    from django.utils.timezone import now as conditional_now
except ImportError:
    from datetime import datetime
    conditional_now = datetime.now


import logging


def configured_message_classes() -> dict:
    """[summary]

    :return: [description]
    :rtype: dict
    """
    conf_dict = getattr(settings, 'DRIP_MESSAGE_CLASSES', {})
    if 'default' not in conf_dict:
        conf_dict['default'] = 'drip.drips.DripMessage'
    return conf_dict


def message_class_for(name: str):
    path = configured_message_classes()[name]
    mod_name, klass_name = path.rsplit('.', 1)
    mod = import_module(mod_name)
    klass = getattr(mod, klass_name)
    return klass


class DripMessage(object):
    """[summary]

    :param object: [description]
    :type object: [type]
    """

    def __init__(self, drip_base, user):
        self.drip_base = drip_base
        self.user = user
        self._context = None
        self._subject = None
        self._pre_header = None
        self._body = None
        self._sms = None
        self._plain = None
        self._message = None

    def fill_text_with_context_data(self, text):
        return Template(text).render(self.context)

    @property
    def from_email(self):
        return self.drip_base.from_email

    @property
    def from_email_name(self):
        return self.drip_base.from_email_name

    @property
    def context(self):
        if not self._context:
            self._context = Context({'user': self.user})
        return self._context

    @property
    def subject(self):
        if not self._subject:
            self._subject = self.fill_text_with_context_data(
                self.drip_base.subject_template
            )
        return self._subject

    @property
    def pre_header(self):
        if not self._pre_header:
            self._pre_header = self.fill_text_with_context_data(
                self.drip_base.pre_header_text
            )
        return self._pre_header

    @property
    def body(self):
        if not self._body:
            self._body = self.fill_text_with_context_data(
                self.drip_base.body_template
            )
        return self._body

    @property
    def sms(self):
        if not self._sms:
            self._sms = self.fill_text_with_context_data(
                self.drip_base.sms_text
            )
        return self._sms

    @property
    def plain(self):
        if not self._plain:
            self._plain = self.pre_header + ' ' + strip_tags(self.body) \
                if self.pre_header else strip_tags(self.body)
        return self._plain

    def get_from_(self):
        if self.drip_base.from_email_name:
            from_ = "{name} <{email}>".format(
                name=self.drip_base.from_email_name,
                email=self.drip_base.from_email,
            )
        else:
            from_ = self.drip_base.from_email
        return from_

    @property
    def message(self):
        if not self._message:
            from_ = self.get_from_()

            self._message = EmailMultiAlternatives(
                self.subject,
                self.plain, from_,
                [self.user.email],
            )

            # check if there are html tags in the rendered template
            if len(self.plain) != len(self.body):
                self._message.attach_alternative(self.body, 'text/html')
        return self._message


class DripBase(object):
    """
    A base object for defining a Drip.

    You can extend this manually, or you can create full querysets
    and templates from the admin.
    """
    #: needs a unique name
    name = None
    subject_template = None
    pre_header_text = None
    body_template = None
    sms_text = None
    from_email = None
    from_email_name = None

    def __init__(self, drip_model, *args, **kwargs):
        self.drip_model = drip_model

        self.name = kwargs.pop('name', self.name)
        self.from_email = kwargs.pop('from_email', self.from_email)
        self.from_email_name = kwargs.pop(
            'from_email_name',
            self.from_email_name,
        )
        self.subject_template = kwargs.pop(
            'subject_template',
            self.subject_template,
        )
        self.pre_header_text = kwargs.pop(
            'pre_header_text',
            self.pre_header_text,
        )
        self.body_template = kwargs.pop('body_template', self.body_template)
        self.sms_text = kwargs.pop('sms_text', self.sms_text)
        if not self.name:
            raise AttributeError('You must define a name.')

        self.now_shift_kwargs = kwargs.get('now_shift_kwargs', {})

    #########################
    #   DATE MANIPULATION   #
    #########################

    def now(self):
        """
        This allows us to override what we consider "now", making it easy
        to build timelines of who gets what when.
        """
        return conditional_now() + self.timedelta(**self.now_shift_kwargs)

    def timedelta(self, *a, **kw):
        """
        If needed, this allows us the ability
        to manipulate the slicing of time.
        """
        from datetime import timedelta
        return timedelta(*a, **kw)

    def walk(self, into_past: int = 0, into_future: int = 0):
        """Walk over a date range and create
            new instances of self with new ranges.

        :param into_past: [description], defaults to 0
        :type into_past: int, optional
        :param into_future: [description], defaults to 0
        :type into_future: int, optional
        :return: [description]
        :rtype: [type]
        """
        walked_range = []
        for shift in range(-into_past, into_future):
            kwargs = dict(
                drip_model=self.drip_model,
                name=self.name,
                now_shift_kwargs={'days': shift},
            )
            walked_range.append(self.__class__(**kwargs))
        return walked_range

    def apply_queryset_rules(self, qs: str) -> str:
        """First collect all filter/exclude kwargs and apply any annotations.
        Then apply all filters at once, and all excludes at once.

        :param qs: [description]
        :type qs: str
        :return: [description]
        :rtype: str
        """
        clauses = {
            'filter': [],
            'exclude': [],
        }

        for rule in self.drip_model.queryset_rules.all():

            clause = clauses.get(rule.method_type, clauses['filter'])

            kwargs = rule.filter_kwargs(qs, now=self.now)
            clause.append(Q(**kwargs))

            qs = rule.apply_any_annotation(qs)

        if clauses['exclude']:
            qs = qs.exclude(functools.reduce(operator.or_, clauses['exclude']))
        qs = qs.filter(*clauses['filter'])

        if self.drip_model.queryset_rules.count() == 0:
            qs = qs.none()

        return qs

    ##################
    #   MANAGEMENT   #
    ##################

    def get_queryset(self):
        """[summary]

        [extended_summary]

        :return: [description]
        :rtype: [type]
        """
        queryset = getattr(self, '_queryset', None)
        if queryset is None:
            self._queryset = self.apply_queryset_rules(
                self.queryset(),
            ).distinct()
        return self._queryset

    def run(self) -> int:
        """Get the queryset, prune sent people, and send it.

        [extended_summary]

        :return: [description]
        :rtype: int
        """
        if not self.drip_model.enabled:
            return None

        self.prune()
        count = self.send()

        return count

    def prune(self):
        """Do an exclude for all Users who have a SentDrip already.
        """
        target_user_ids = self.get_queryset().values_list('id', flat=True)
        exclude_user_ids = SentDrip.objects.filter(
            date__lt=conditional_now(),
            drip=self.drip_model,
            user__id__in=target_user_ids
        ).values_list('user_id', flat=True)
        self._queryset = self.get_queryset().exclude(id__in=exclude_user_ids)

    def get_count_from_queryset(self, MessageClass) -> int:
        count = 0
        for user in self.get_queryset():
            message_instance = MessageClass(self, user)
            try:
                if not settings.DRIP_CAMPAIGN_DRYRUN:
                    result = message_instance.message.send()
                    if result:
                        SentDrip.objects.create(
                            drip=self.drip_model,
                            user=user,
                            from_email=self.from_email,
                            from_email_name=self.from_email_name,
                            subject=message_instance.subject,
                            pre_header=message_instance.pre_header,
                            body=message_instance.body,
                            sms=message_instance.sms,
                        )
                post_drip.send(
                    sender=self.drip_model,
                    drip=message_instance,
                    user=user
                )
                count += 1
            except Exception as e:
                logging.error(
                    "Failed to send drip {drip} to user {user}: {err}".format(
                        drip=self.drip_model.id,
                        user=str(user),
                        err=str(e),
                    )
                )
        return count

    def send(self):
        """Send the message to each user on the queryset.

        Create SentDrip for each user that gets a message.

        Returns count of created SentDrips.
        """

        if not self.from_email:
            self.from_email = getattr(
                settings,
                'DRIP_FROM_EMAIL',
                settings.DEFAULT_FROM_EMAIL,
            )
        MessageClass = message_class_for(self.drip_model.message_class)

        return self.get_count_from_queryset(MessageClass)

    ####################
    #   USER DEFINED   #
    ####################

    def queryset(self):
        """
        Returns a queryset of auth.User who meet the
        criteria of the drip.

        Alternatively, you could create Drips on the fly
        using a queryset builder from the admin interface...
        """
        User = get_user_model()
        return User.objects

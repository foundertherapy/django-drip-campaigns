from modeltranslation.translator import register, translator
from modeltranslation.translator import TranslationOptions
from drip.models import Drip, LimitedAccessDrip


@register(Drip)
class DripTranslationOptions(TranslationOptions):
    fields = (
        'subject_template',
        'pre_header_text',
        'body_html_template',
        'sms_text'
    )


translator.register(LimitedAccessDrip, DripTranslationOptions)

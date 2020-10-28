from modeltranslation.translator import register, TranslationOptions
from drip.models import Drip


@register(Drip)
class DripTranslationOptions(TranslationOptions):
    fields = (
        'subject_template',
        'pre_header_text',
        'body_html_template',
        'sms_text'
    )


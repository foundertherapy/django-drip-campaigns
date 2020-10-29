# MUST SPECIFY TO MAKE USE OF DJANGO DRIP
DRIP_FROM_EMAIL = ''
DEBUG = True

"""
To disable the library from sending emails and send it yourself using
the post_drip signal.
"""
DRIP_CAMPAIGN_DRYRUN = False

"""
To Add permission to some admins to control the drips and not all admins
"""
ENABLE_QUERY_SET_RULE_PERMISSION = False

DRIP_ADMIN_HELP_TEXT = ''

SECRET_KEY = 'whatever/you/want-goes-here'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite.db',
    },
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.messages',

    'drip',

    # testing only
    'credits',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

USE_TZ = True
TIME_ZONE = 'UTC'

AUTH_PROFILE_MODULE = 'credits.Profile'

ROOT_URLCONF = 'test_urls'

STATIC_URL = '/static/'
STATICFILES_DIRS = ()

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

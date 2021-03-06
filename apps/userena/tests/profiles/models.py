from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.userena.models import UserenaBaseProfile
from apps.userena.utils import user_model_label

import datetime

class Profile(UserenaBaseProfile):
    """ Default profile """
    GENDER_CHOICES = (
        (1, _('Male')),
        (2, _('Female')),
    )

    user = models.OneToOneField(user_model_label,
                                unique=True,
                                verbose_name=_('user'),
                                related_name='profile')

    gender = models.PositiveSmallIntegerField(_('gender'),
                                              choices=GENDER_CHOICES,
                                              blank=True,
                                              null=True)
    website = models.URLField(_('website'), blank=True)
    location =  models.CharField(_('location'), max_length=255, blank=True)
    about_me = models.TextField(_('about me'), blank=True)

class SecondProfile(UserenaBaseProfile):
    user = models.OneToOneField(user_model_label,
                                unique=True,
                                verbose_name=_('user'),
                                related_name='profile_second')

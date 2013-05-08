from django.conf.urls import patterns, include, url
# from django.views.generic.simple import direct_to_template
from django.conf.urls.static import static
from django.conf import settings
from nesss import views

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', views.home, name='home'),
    url(r'^accounts/', include('apps.userena.urls')),
    url(r'^grappelli/',include('apps.grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
    
)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


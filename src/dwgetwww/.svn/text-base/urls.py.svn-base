from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
import iface.views

urlpatterns = patterns('',
     (r'^$', iface.views.index),
     (r'^manage/list$', iface.views.listQueried),
     (r'^manage/list/remove/(?P<IP>[0-9.]+)/(?P<port>\d+)$', iface.views.listRemove),
     (r'^manage/list/add$', iface.views.listAdd),
     (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),)


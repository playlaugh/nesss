from django.conf.urls.defaults import *

urlpatterns = patterns('',
	# Example:

	# main page
    url(r'^$', 'exams.list.list_exams', name="exam-list"),
	url(r'^view/(?P<exam_id>\d+)/$', 'exams.views.view', name="exam-view"),    
	url(r'^edit/(?P<exam_id>\d+)/$', 'exams.views.edit', name="exam-edit"),    
	url(r'^submit/$', 'exams.views.submit', name="exam-submit"),

	url(r'^list-incomplete/$', 'exams.list.list_incomplete', name="exam-list-incomplete"),
	url(r'^exam_autocomplete/$', 'exams.views.exam_autocomplete', name='exams-autocomplete'),
)

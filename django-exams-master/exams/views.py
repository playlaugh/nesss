from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
import math

from courses.models import *
from exams.models import Exam, DuplicateExamError, UnpublishableExamError
from exams.forms import *

from ajaxlist.helpers import render_ajaxlist_response, get_ajaxinfo, sort_objects, paginate_objects

import logging

def maintenance(fn):
    def pred(user):
        if not user.is_superuser:
            if user.message_set.count() == 0:
                user.message_set.create(message="The section you requested is currently down for maintenance")
            return False
        return True
#    return user_passes_test(pred, '/')(fn)
    return fn


@maintenance
def view(request, exam_id):
    pass

@maintenance
def edit(request, exam_id):
    exam = get_object_or_404(Exam, pk=int(exam_id))
    return _edit(request, exam, reverse('exam-list-incomplete'))

@maintenance
def submit(request):
    return _edit(request, None, None)

def _edit(request, exam, after):
    if request.POST:
        form = ExamForm(request, exam, request.POST, request.FILES)
        if form.is_valid():
            try:
                e = form.save()
                ident = "anonymous"
                if request.user.is_authenticated():
                    ident = request.user.username
                    request.user.message_set.create(message="Exam uploaded successfully!")
                logging.getLogger('special.actions').info("Exam submitted: %s by %s" % (e.file.name, ident))
                if after:
                    return HttpResponseRedirect(after)
            except DuplicateExamError:
                request.user.message_set.create(message="The exam you attempted to upload already exists in our database!")
            except UnpublishableExamError:
                request.user.message_set.create(message="You specified for the exam to be publishable, but it must first be complete!")
            form = ExamForm(request, exam)
    else:
        form = ExamForm(request, exam)
    
    return render_to_response("exam/edit_exam.html", {"form" : form}, context_instance=RequestContext(request))    

@maintenance
def exam_autocomplete(request):
    def iter_results(courses):
        if courses:
            for r in courses:
                yield '%s|%s\n' % (r.short_name(space = True), r.id)
    
    if not request.GET.get('q'):
        return HttpResponse(mimetype='text/plain')
    
    q = request.GET.get('q')
    limit = request.GET.get('limit', 15)
    try:
        limit = int(limit)
    except ValueError:
        return HttpResponseBadRequest() 

    courses = filter(lambda x: x.exam_count > 0, Course.objects.ft_query(q).annotate_exam_count())[:limit]
    return HttpResponse(iter_results(courses), mimetype='text/plain')


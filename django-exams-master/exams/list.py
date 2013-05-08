from django.shortcuts import get_object_or_404, render_to_response
from django.template.loader import get_template
from django.template import RequestContext
from django.core import urlresolvers
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.datastructures import SortedDict
from django.conf import settings

from ajaxlist import get_list_context, filter_objects
from ajaxlist.helpers import get_ajaxinfo, render_ajaxlist_response, sort_objects, paginate_objects
from courses.models import *
from string import atoi
from nice_types.semester import Semester

from exams.constants import FILE_UPLOAD_DIR, EXAM_TYPE
from exams.models import Exam




_EXAM_FILTER_FUNCTIONS = SortedDict()
_EXAM_FILTER_FUNCTIONS["exam_department"] = lambda objects, value: (objects.query_department(value), 
                                                                "in department \"%s\"" % (value))
_EXAM_FILTER_FUNCTIONS["exam_coursenumber"] = lambda objects, value: (objects.query_coursenumber(value), \
                                                                "with course number containing \"%s\"" % (value))
_EXAM_FILTER_FUNCTIONS["exam_coursenumber_exact"] = lambda objects, value: (objects.query_coursenumber_exact(value), \
                                                                "with course number \"%s\"" % (value))
_EXAM_FILTER_FUNCTIONS["exam_instructor"] = lambda objects, value: (objects.query_instructor(value), \
                                                                "from instructor \"%s\"" % (value))
_EXAM_FILTER_FUNCTIONS["exam_after"] = lambda objects, value: (objects.after(value), \
                                                                "after \"%s\"" % (Semester(value).verbose_description()))

def filter_exams(objects, filters):
    if len(filters) == 0:
        return Exam.published.none(), None
    
    filter_descriptions = []
    for filter_type in _EXAM_FILTER_FUNCTIONS.keys():
        if not filters.has_key(filter_type):
            continue
        values = [filters[filter_type]]
        filter_function = _EXAM_FILTER_FUNCTIONS[filter_type]
        filtered_objects = Exam.published.none()
        for value in values:
            filtered, description = filter_function(objects, value)
            filtered_objects = filtered_objects | filtered
            filter_descriptions.append((filter_type, description))
        objects = filtered_objects
    #return objects.distinct()
    return objects, filter_descriptions


def describe_filters(exam_filters):
    filters = []
    try:
        filters.append("after %s" % Semester(exam_filters["exam_after"]).verbose_description())
    except:
        pass

    try:
        filters.append("for course \"%s %s\"" % (exam_filters["exam_department"], exam_filters["exam_coursenumber"]))
    except:
        try:
            filters.append("in department \"%s\"" % (exam_filters["exam_department"]))
        except:
            pass

    try:
        filters.append("from instructor \"%s\"" % exam_filters["exam_instructor"])
    except:
        pass

    if len(filters) == 3:
        return "%s, %s, and %s" % tuple(filters)
    return " and ".join(filters)
    
def get_new_dict(headers):
    d = SortedDict()
    for h in headers:
        d[h] = []
    return d

def regroup_exams(exams):
    exams = exams.order_by('-semester', 'exam_type', 'number', 'has_solutions')
    d = SortedDict()
    
    headers = []
    for e in exams:
        k = e.describe_exam_type()
        if k not in headers:
            headers.append(k)

    for e in exams:
        k1 = (e.semester.verbose_description(), e.instructor_names)
        k2 = e.describe_exam_type()
        if not d.has_key(k1):
            d[k1] = get_new_dict(headers)

        if d[k1].has_key(k2):
            d[k1][k2].append(e)
        else:
            d[k1][k2] = [e]

    return d, headers

def view_course(exams, course_id):
    exams, headers = regroup_exams(exams)
    return { 
        'template' : 'exam/_view_course.html',
        'course' : Course.objects.get(pk=course_id),
        'exams' : exams,
        'headers' : headers,
    }

def browse_one_department(department, view_all=False):
    courses = department.course_set.all().annotate_exam_count()

    courses = courses.filter(exam__isnull=False).distinct()
    if not view_all:
        courses = courses.filter(exam__publishable=True).distinct()

    courses = courses.annotate_exam_count().order_by('pk')
    return {
        'template' : 'exam/_browse_one.html',
        "courses" : courses, 
        "department" : department
    }
    
def browse_many_departments(departments):
    return {
        'template' : 'exam/_browse_many.html',
        'departments' : departments,
    }

def browse_popular_departments():
    departments = Department.objects.filter(exam__isnull=False).distinct().get_top_departments_by_published_exams()

    #departments = list(departments[:10])
    departments.sort(key=lambda x: x.name)
    return {
        'template' : 'exam/_browse_many.html',
        'departments' : departments,
    }

def list_exams(request):
    d = get_ajaxinfo(request.GET)
    
    view_unpublished = False
    if request.user.has_perm('exam.add_exam'):
        view_unpublished = True
    d['view_unpublished'] = view_unpublished
    
    exam_filters = dict((k, v) for k, v in request.GET.items() if k.startswith("exam_") and len(v) > 0)    
    exams, descriptions = filter_exams(Exam.all.filter(complete=True) if view_unpublished else Exam.published.all(), exam_filters)
    d['filter_descriptions'] = descriptions

    if not descriptions:
        d.update(browse_popular_departments())
    elif exams.count() == 0:
        d['no_results'] = True
    else:
        related_ids = exams.values_list('course', 'department').distinct()
        course_ids = set(rid[0] for rid in related_ids)
        if len(course_ids) == 1:
            d.update(view_course(exams, course_ids.pop()))
        else:
            department_ids = set(rid[1] for rid in related_ids)
            if len(department_ids) == 1:
                d.update(browse_one_department(Department.objects.get(pk=department_ids.pop()), request.user.has_perm("exam.add_exam")))
                d['cache_key'] = d['department'].pk
            else:
                departments = Department.objects.filter(id__in=department_ids).order_by('name')
                d.update(browse_many_departments(departments))
                d['cache_key'] = ",".join(str(dept.pk) for dept in d['departments'])
    for k in _EXAM_FILTER_FUNCTIONS.keys():
        d[k] = exam_filters.get(k, '')
    return render_ajaxlist_response(request.is_ajax(), "exam/list_exams.html", d, context_instance=RequestContext(request))

@user_passes_test(lambda u: u.is_superuser)
def list_incomplete(request):
    d = get_ajaxinfo(request.GET)
    if d['sort_by'] == '?':
        d['sort_by'] = 'submitted'

    incompletes = Exam.incomplete.all()
    incompletes = sort_objects(incompletes, d['sort_by'], None)
    incompletes = paginate_objects(incompletes, d, page=d['page'])

    d['incompletes'] = incompletes
    
    return render_ajaxlist_response(request.is_ajax(), "exam/list_incomplete.html", d, context_instance=RequestContext(request))

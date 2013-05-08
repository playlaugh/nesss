import datetime, re, os, string, os.path, random

from django.contrib.auth.models import User, Permission

from courses.models import *
from constants import FILE_UPLOAD_DIR, EXAM_TYPE

from django.db.models import Q
from django.db.models.query import QuerySet
from nice_types.db import QuerySetManager
from nice_types.semester import Semester

import hashlib, base64

from django import db

class ExamManager(QuerySetManager):
        def query_course(self, query):                          
            return self.get_query_set().query_course(query)
        def query_department(self, query):                          
            return self.get_query_set().query_department(query)
        def query_coursenumber(self, query):                          
            return self.get_query_set().query_coursenumber(query)
        def query_coursenumber_exact(self, query):
            return self.get_query_set().query_coursenumber_exact(query)
        
        def query_instructor(self, query):   
            return self.get_query_set().query_instructor(query)    
            
        def after(self, value):
            return self.get_query_set().after(value)  
            
            
class PublishedExamManager(ExamManager):
        def get_query_set(self):
            return super(PublishedExamManager, self).get_query_set().filter(publishable=True, complete=True)

class UnpublishedExamManager(ExamManager):
        def get_query_set(self):
            return super(UnpublishedExamManager, self).get_query_set().filter(publishable=False, complete=True) 

class IncompleteExamManager(ExamManager):
        def get_query_set(self):
            return super(IncompleteExamManager, self).get_query_set().filter(complete=False)

class UnpublishableExamError(Exception):
    pass

class DuplicateExamError(Exception):
    pass

class Exam(db.models.Model):
    """ Models an exam. """
    all = ExamManager()    
    published = PublishedExamManager()
    unpublished = UnpublishedExamManager()
    incomplete = IncompleteExamManager()

    # file_hash is primary key
    
    klass = db.models.ForeignKey(Klass, null = True)
    """ The particular klass in which the exam was given. """
    
    course = db.models.ForeignKey(Course, null=True)
    """ The course this exam is for (cached) """
    
    department = db.models.ForeignKey(Department, null=True)
    """ The department this exam is for (cached) """    

    semester = SemesterField(null=True)
    """ The semester this exam was administered """

    instructors = db.models.ManyToManyField(Instructor)
    """ The instructors associated with this exam """

    unmatched_instructor_names = models.CharField(max_length = 200)
    """ The names of unmatched instructors """

    cached_instructor_names = models.CharField(max_length = 200, null=True)
    """ cached instructor names """
    
    file = db.models.FileField(null = True, upload_to = FILE_UPLOAD_DIR)
    """ The local filesystem path to where the actual exam is stored. """

    file_hash = db.models.CharField(max_length=50, unique=True, primary_key=True)
    """ a hash of the file contents """
    
    exam_type = db.models.CharField(max_length=50, null=True)
    """ The type of exam (e.g., Midterm, Final). """
    
    number = db.models.CharField(max_length=50, blank=True, null=True)
    """ The exam number. If unique (i.e., only one final), leave this field blank. """ 
    
    version = db.models.CharField(max_length = 1, blank = True)
    """ The version of the exam. If only one version, leave this field blank. """

    has_solutions = db.models.BooleanField()
    """ True if this is the solutions file (i.e., not the original exam). """

    is_practice = db.models.BooleanField()
    """ True if this is a practice exam """

    is_makeup = db.models.BooleanField()
    """ True if this is a makeup exam """
    
    publishable = db.models.BooleanField()
    """ set true if it should be published online; false if no publish; complete must be True for this to have affect """

    submitter = db.models.ForeignKey(User, null = True)
    """ the person who submitted this exam """
    
    submitted = db.models.DateTimeField()
    """ when this exam was submitted """
    
    exam_date = db.models.DateTimeField(null=True)
    """ when the exam was administered. used for sorting """   

    complete = db.models.BooleanField()
    """ whether the exam's information is complete and can be published """

    comment = db.models.TextField()
    """ non-public comment attached to exam """

    def _instructor_names(self):
        return self.cached_instructor_names or self.unmatched_instructor_names
    instructor_names = property(_instructor_names)

    def _updated_instructor_names(self):
        self.cached_instructor_names = "; ".join([inst.last for inst in self.instructors.all()])
        if len(self.cached_instructor_names) > 0:
            self.unmatched_instructor_names = ""
        return self.instructor_names
    updated_instructor_names = property(_updated_instructor_names)
    

    def __unicode__(self):
        s = u"%s %s %s %s" % (self.course, self.semester.abbr(), EXAM_TYPE.get_name_from_value(self.exam_type), self.number)
        if self.has_solutions:
            s += u" Solutions"
        if self.is_practice:
            s += u" (practice)"
        if self.is_makeup:
            s += u" (makeup)"
        if not self.publishable:
            s += u" (unpublishable)"
        return s

    def request_confirmation(self):
        import request.utils
        return request.utils.request_confirmation(self, self.submitter, Permission.objects.get(codename="add_exam"))
    
    DIGITS_PATTERN = re.compile("(?P<digits>\d+)")
    @property
    def integer_number(self):
        m = Exam.DIGITS_PATTERN.search(self.number)
        if m:
            return int(m.group('digits'))
        return 0
        
    class QuerySet(QuerySet):
        def query_course(self, query):              
            courses = Course.objects.ft_query(query)
            return self.filter(course__in = courses)

        def query_department(self, query):              
            departments = Department.objects.ft_query_all(query)
            return self.filter(department__in = departments)

        def query_coursenumber(self, query):              
            prefix, number, suffix = Course.split_coursenumber(query)
            self = self.filter(course__number__istartswith = number)
            if len(prefix) > 0:
                self = self.filter(course__prefix=prefix.upper())
            if len(suffix) > 0:
                self = self.filter(course__suffix=suffix.upper())
            return self

        def query_coursenumber_exact(self, query):
            return self.filter(course__coursenumber__iexact = query)
        
        def query_instructor(self, query):
            instrs = Instructor.objects.none()
            for instr in query.split(";"):
                instrs = instrs | Instructor.objects.ft_query(instr)
            if instrs.count() > 0:
                self1 = self.filter(instructors__in = instrs)
            self2 = self
            for instr in query.split(";"):
                self2 = self2.filter(cached_instructor_names__icontains=instr) | self2.filter(unmatched_instructor_names__icontains=instr)
            return self & (self1 | self2)
#            (last, first, dd) = Instructor.objects.parse_query(query)

#            if first and last:
#                return self.filter(instructors__first__icontains = first, instructors__last__icontains = last)
#            elif last:
#                return self.filter(instructors__last__icontains = last)            
#            return self
            
        def after(self, value):
            if len(value) != 4:
                return self
            return self.filter(exam_date__gte = Semester(value).start_date)
    
    
    def describe_exam_type(self):
        if self.exam_type == EXAM_TYPE.FINAL:
            return EXAM_TYPE.get_name_from_value(EXAM_TYPE.FINAL)
        else:
            return "%s %s" % (EXAM_TYPE.get_name_from_value(self.exam_type), self.number)
                
    def get_exam_description(self, course=False, semester=False, instructors=False):
        description = []
        if course:
            description.append(str(self.course))
            
        if semester:
            description.append(str(self.semester))
            
        description.append(self.describe_exam_type())
        
        if instructors:
            description.append("[%s]" % self.instructor_names())
        
        return " ".join(description)
            
        
    def get_exam_format(self):
        return os.path.splitext(self.file.name)[1].strip(". ")
    
    def get_exam_filename(self):
        if self.complete:
            tokens = [self.course.short_name(), str(self.semester), self.instructor_names, EXAM_TYPE.get_abbr_from_value(self.exam_type, self.exam_type)]
            if self.number not in (None, "", "0"):
                tokens.append(self.number)

            maybe = (('s' if self.has_solutions else '') + ('p' if self.is_practice else '') + ('m' if self.is_makeup else ''))
            if maybe:
                tokens.append(maybe)
            return "__".join(tokens).replace(" ", "-")
        return "AUTO_%.8d" % random.randint(1, 1000000)

    def rename_exam(self):
        if not self.complete:
            return
        file_name = self.file.name
        final_name = self.get_exam_filename() + os.path.splitext(file_name)[1]
        if file_name == (FILE_UPLOAD_DIR + "/" + final_name):
            return
        final_path = os.path.join(os.path.dirname(self.file.path), final_name)
        while os.path.exists(final_path):
            path, ext = os.path.splitext(final_path)
            path += "_"
            final_path = path + ext
        os.rename(self.file.path, final_path)
        self.file = FILE_UPLOAD_DIR + "/" + os.path.basename(final_path)
        self.save(no_rename=True)
        
    def get_semester_sort(self):
        return self.semester.start_date
    
    def auto_exam_date(self):
        semester_start_date = self.semester.start_date
        weights = {EXAM_TYPE.MIDTERM : 7, EXAM_TYPE.QUIZ : 1, EXAM_TYPE.FINAL : 30, EXAM_TYPE.REVIEW : 29}
        if self.number:
            days_delta = (1 + self.integer_number) * weights[self.exam_type]
        else:
            days_delta = weights[self.exam_type]
        return semester_start_date + datetime.timedelta(days = days_delta)

    def can_complete(self):
        return bool(self.course and self.semester and self.exam_type and self.number != None)
   
    def save(self, no_rename=False, *args, **kwargs):
        if self.klass_id:
            self.course_id = self.klass.course_id
            self.semester = self.klass.semester
            self.cached_instructor_names = self.klass.instructor_names
        if self.course_id:
            self.department_id = self.course.department_id
        if self.semester and self.exam_type and self.number:
            self.exam_date = self.auto_exam_date()

        self.complete = self.can_complete()
        publishable_error = False
        if self.publishable and not self.complete:
            publishable_error = True
            self.publishable = False
        if not self.submitted:
            self.submitted = datetime.datetime.now()
        if self.file and self.file.size > 0 and not self.file_hash:
            hash = hashlib.md5()
            for chunk in self.file.chunks():
                hash.update(chunk)
            self.file_hash = base64.urlsafe_b64encode(hash.digest())
        if self.file_hash:
            dupe = Exam.all.filter(file_hash=self.file_hash).exclude(pk=self.pk)
            if len(dupe) > 0:
                raise DuplicateExamError("Duplicate exam exists with hash '%s'" % self.file_hash, dupe[0])

        if not self.unmatched_instructor_names:
            self.unmatched_instructor_names = ""

        super(Exam, self).save(*args, **kwargs)

        if self.klass_id:
            self.instructors = self.klass.instructors.all()
        if publishable_error:
            raise UnpublishableExamError("Exam can't be published if it is incomplete! ")
        if self.complete and not no_rename:
            self.rename_exam()

        if not self.instructor_names:
            self._updated_instructor_names()
            super(Exam, self).save(*args, **kwargs)
        
from exams.requests import *

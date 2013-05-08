from django import forms
from django.core.files.base import ContentFile
from django.core import urlresolvers
from string import atoi
import datetime

from courses.constants import SEMESTER
from courses.models import *
from courses.forms.widgets import DepartmentAutocomplete, CourseNumberAutocomplete, InstructorAutocomplete, CourseAutocomplete
from courses.forms.fields import InstructorAutocompleteField, CourseAutocompleteField

from exams.models import Exam

from nice_types import semester
from nice_types.otherchoicefield import OtherChoiceField

import os

from exams.constants import EXAM_TYPE, EXAM_NUMBER, VALID_EXTENSIONS

INITIAL_SEMESTER_VALUE = semester.Semester('fa90')

def get_exam_type_choices():
    values = Exam.all.values_list('exam_type', flat=True).distinct()
    return ((v, EXAM_TYPE.get_name_from_value(v, v)) for v in values)

def get_exam_number_choices():
    values = Exam.all.values_list('number', flat=True).distinct()
    return ((v, EXAM_NUMBER.get_name_from_value(v, v)) for v in values)

THIS_YEAR = datetime.date.today().year
EXAM_SEASONS = (("sp", "Spring"), ("su", "Summer"), ("fa", "Fall"))
EXAM_YEARS = [(str(x), x) for x in range(THIS_YEAR, THIS_YEAR-5, -1)]
class ExamForm(forms.Form):
    course = CourseAutocompleteField(required=False)
    instructor1 = InstructorAutocompleteField(label="Primary Instructor", required=False)
    instructor2 = InstructorAutocompleteField(label="Secondary Instructor", required=False)
    semester = semester.SemesterSplitFormField(seasons=EXAM_SEASONS, years=EXAM_YEARS, initial=INITIAL_SEMESTER_VALUE, required=False)
    
    exam_type = OtherChoiceField(choices=get_exam_type_choices, required=False, initial=EXAM_TYPE.MIDTERM, field_class=forms.CharField(max_length=50))

    number = OtherChoiceField(choices=get_exam_number_choices, required=False, initial=EXAM_NUMBER.BLANK, field_class=forms.CharField(max_length=50))
    
    number = forms.CharField(required = False)
    version = forms.CharField(required = False)
    has_solutions = forms.BooleanField(required = False)
    
    exam_file = forms.FileField()

    comment = forms.CharField(label="Comment", help_text="Any additional information that can help identify the exam?", widget=forms.Textarea(attrs={"rows":"5", "cols":"30"}), required=False)

    def __init__(self, request, exam, *args, **kwargs):
        self.request = request
        self.exam = exam
        if exam and len(args) == 0:
            args = [exam.__dict__]
        super(ExamForm, self).__init__(*args, **kwargs)
        if request.user.is_superuser:
            self.fields['publishable'] = forms.BooleanField(label="Publishable", required=False)
            self.fields['complete'] = forms.BooleanField(label="Complete", required=False)
            self.fields['exam_file'].required = False
        
    def clean_exam_file(self):
        uf = self.cleaned_data["exam_file"]
        if not uf:
            return None
        ext = os.path.splitext(uf.name)[1]
        if ext not in VALID_EXTENSIONS:
            raise forms.ValidationError("Filetype must be one of: " + ", ".join(VALID_EXTENSIONS))
        self.cleaned_data["exam_file_extension"] = ext
        return uf
        
    #def clean(self):
    #    d = self.cleaned_data
    #    if d.has_key("course_object") and d.has_key("semester"):
    #        klasses = Klass.objects.filter(course = d["course_object"], semester=d["semester"])
    #        if len(klasses) == 0:
    #            raise forms.ValidationError("No klasses for that course and semester")
    #        elif len(klasses) >= 2:
    #            potential_instructors = ", ".join([k.instructor_names for k in klasses])
    #            klasses = self.filter_klasses_by_instructor(klasses)
    #            if len(klasses) == 0:
    #                raise forms.ValidationError("More than 1 klass for that course and semester, but the provided instructor didn't teach any sections; try specifying an instructor from: %s" % (potential_instructors,))
    #            elif len(klasses) >= 2:
    #                raise forms.ValidationError("More than 1 klass for that course, semester, and instructor; try specifying an instructor from %s" % (potential_instructors,))
    #        self.cleaned_data["klass"] = klasses[0]
    #    return self.cleaned_data

    def save(self):
        exam = self.exam
        if not exam:
            exam = Exam()

        data = self.cleaned_data    

        exam.publishable = False
        exam.paper_only = False

        fields = ['has_solutions', 'version', 'number', 'exam_type', 'semester']
        if self.request.user.is_superuser:
            fields += ["publishable", "complete"]

        for field in fields:
            setattr(exam, field, data[field])

        if exam.semester == INITIAL_SEMESTER_VALUE:
            exam.semester = None

        exam.comment = exam.comment or ''
        if exam.comment.find('FILENAME:') == -1:
            exam.comment += "\nFILENAME: '%s'\n" % data['exam_file'].name

        if not exam.submitter and not self.request.user.is_anonymous():
            exam.submitter = self.request.user

        if data.has_key('course'):
            exam.course = data['course']
        if data.has_key("exam_file_extension"):
            exam.file.save(exam.get_exam_filename() + data["exam_file_extension"], ContentFile(data['exam_file'].read()))
        else:
            exam.save()
        #instructors = [instr for instr in [data.get(field, None) for field in ("instructor1", "instructor2")] if instr is not None]
	
        #instrs = [data.get(field, None) for field in ("instructor1", "instructor2")]
        #instructors = filter(lamdba x: x is not None, instrs)

        instructors = []
        if 'instructor1' in data:
                instructors.append(data['instructor1'])
        if 'instructor2' in data:
                instructors.append(data['instructor2'])

        if instructors:
            exam.instructors = instructors
                
        return exam


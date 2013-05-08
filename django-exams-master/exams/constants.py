from nice_types import enum

FILE_UPLOAD_DIR = 'exam'

VALID_EXTENSIONS = ["doc", ".pdf", ".html", ".htm", ".txt"]

class EXAM_TYPE( enum.Enum ):
    MIDTERM = enum.EnumValue("10_mt", "Midterm", abbr="mt")
    FINAL = enum.EnumValue("20_final", "Final", abbr="f")
    REVIEW = enum.EnumValue("30_review", "Review", abbr="review")
    QUIZ = enum.EnumValue("40_quiz", "Quiz", abbr="quiz")

class EXAM_NUMBER( enum.Enum ):
    BLANK = enum.EnumValue('', "No number (e.g. final)")

class EXAMS_PREFERENCE( enum.Enum ):
    UNKNOWN = enum.EnumValue(0, 'Unknown')
    NEVER_OK = enum.EnumValue(5, 'Never post exams')
    ALWAYS_ASK = enum.EnumValue(10, 'Always ask before posting exams')
    ALWAYS_OK = enum.EnumValue(15, 'Always OK to post exams')


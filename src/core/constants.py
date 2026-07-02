"""Central technical constants for workbook data architecture."""

STUDENT_ID = "student_id"
FIRST_NAME = "first_name"
LAST_NAME = "last_name"
GROUP_ID = "group_id"
GROUP_NAME = "group_name"
COURSE_ID = "course_id"
COURSE_NAME = "course_name"
COLOR_KEY = "color_key"
COLOR_NAME = "color_name"
COLOR_HEX = "color_hex"
STUDENT_NOTES = "student_notes"
ACTIVE = "active"
CREATED_AT = "created_at"
UPDATED_AT = "updated_at"
ARCHIVED_AT = "archived_at"

SHEET_DATA_STUDENTS = "data_students"
SHEET_DATA_GROUPS = "data_groups"
SHEET_DATA_COURSES = "data_courses"

TABLE_STUDENTS = "tbl_students"
TABLE_GROUPS = "tbl_groups"
TABLE_COURSES = "tbl_courses"

STUDENT_ID_PREFIX = "STU"
GROUP_ID_PREFIX = "GRP"
COURSE_ID_PREFIX = "CRS"
COURSE_GROUP_ID_PREFIX = "CRG"
COMPETENCY_ID_PREFIX = "CMP"
OBSERVATION_ID_PREFIX = "OBS"
MEDIA_ID_PREFIX = "MED"

ID_SEQUENCE_WIDTH = 6

COURSE_COLOR_OPTIONS = (
    ("Blau", "#2563EB"),
    ("Grün", "#16A34A"),
    ("Orange", "#F97316"),
    ("Gelb", "#EAB308"),
    ("Lila", "#9333EA"),
    ("Rot", "#DC2626"),
    ("Grau", "#6B7280"),
)

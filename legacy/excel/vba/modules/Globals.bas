Attribute VB_Name = "Globals"
Option Explicit

Public Const NAME_PROFILE_SELECTED_STUDENT_ID As String = "ui_profile_selected_student_id"
Public Const NAME_PROFILE_BACK_TO_CLASS_OVERVIEW As String = "ui_profile_back_to_class_overview"
Public Const NAME_STUDENT_CARD_PREFIX As String = "ui_student_slot_"
Public Const NAME_STUDENT_CARD_ID_PREFIX As String = "ui_student_slot_id_"
Public Const NAME_CLASS_SEARCH_INPUT As String = "ui_class_search_input"
Public Const NAME_DIALOG_NEW_STUDENT_FIRST_NAME As String = "ui_dialog_new_student_first_name"
Public Const NAME_DIALOG_NEW_STUDENT_LAST_NAME As String = "ui_dialog_new_student_last_name"
Public Const NAME_DIALOG_NEW_STUDENT_GROUP As String = "ui_dialog_new_student_group"
Public Const NAME_DIALOG_NEW_STUDENT_COURSE As String = "ui_dialog_new_student_course"
Public Const NAME_DIALOG_NEW_STUDENT_NOTES As String = "ui_dialog_new_student_notes"
Public Const NAME_DIALOG_NEW_STUDENT_SAVE As String = "ui_dialog_new_student_save"
Public Const SHAPE_STUDENT_CARD_PREFIX As String = "ui_nav_student_card_"
Public Const SHAPE_PROFILE_BACK_PREFIX As String = "ui_nav_profile_back"
Public Const SHAPE_DIALOG_NEW_STUDENT_SAVE As String = "ui_action_save_new_student"
Public Const STUDENT_CARD_SLOT_COUNT As Long = 28
Public Const RUNTIME_COMMAND_FILE_NAME As String = "runtime_command.json"
Public Const RUNTIME_RESULT_FILE_NAME As String = "runtime_result.json"
Public Const RUNTIME_DATABASE_RELATIVE_PATH As String = "data/kompetenzmanager.sqlite"

Public Const VBA_SHAPE_TYPE_RECTANGLE As Long = 1 ' msoShapeRectangle
Public Const VBA_OFFICE_TRUE As Long = -1 ' msoTrue
Public Const VBA_OFFICE_FALSE As Long = 0 ' msoFalse
Public Const VBA_PLACEMENT_MOVE_AND_SIZE As Long = 1 ' xlMoveAndSize
Public Const VBA_Z_ORDER_BRING_TO_FRONT As Long = 0 ' msoBringToFront
Public Const VBA_ENABLE_SELECTION_UNLOCKED_CELLS As Long = 1 ' xlUnlockedCells

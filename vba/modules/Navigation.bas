Attribute VB_Name = "Navigation"
Option Explicit

Public Sub OpenStudentProfileById(ByVal studentId As String)
    If Len(studentId) = 0 Then Exit Sub

    ThisWorkbook.Worksheets(SHEET_STUDENT_PROFILE).Activate
    ThisWorkbook.Worksheets(SHEET_STUDENT_PROFILE).Range(CELL_STUDENT_PROFILE_SELECTED_ID).Value = studentId
End Sub

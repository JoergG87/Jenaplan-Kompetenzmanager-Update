Attribute VB_Name = "Navigation"
Option Explicit

Private Const DEBUG_STUDENT_CARD_NAVIGATION As Boolean = True

Public Sub OpenStudentProfileFromCard()
    Dim shapeName As String
    Dim slotId As String
    Dim studentId As String

    shapeName = ReadCallerShapeName()
    slotId = ReadSlotIdForCardShape(shapeName)
    studentId = ReadStudentIdForSlot(slotId)

    If Len(studentId) = 0 Then
        MsgBox BuildStudentCardNavigationMessage( _
            "Keine student_id fuer die geklickte Karte gefunden.", _
            shapeName, _
            slotId, _
            studentId _
        ), vbExclamation, "Navigation"
        Exit Sub
    End If

    If DEBUG_STUDENT_CARD_NAVIGATION Then
        MsgBox BuildStudentCardNavigationMessage( _
            "Navigationstest: Schuelerkarte erkannt.", _
            shapeName, _
            slotId, _
            studentId _
        ), vbInformation, "Navigation"
    End If

    OpenStudentProfileById studentId
End Sub

Public Sub OpenStudentProfileById(ByVal studentId As String)
    Dim selectedStudentIdRange As Object
    Dim profileSheet As Object

    studentId = Trim$(studentId)
    If Len(studentId) = 0 Then
        MsgBox "Keine student_id fuer die ausgewaehlte Karte gefunden.", vbExclamation, "Navigation"
        Exit Sub
    End If

    Set selectedStudentIdRange = GetWorkbookNameRange(NAME_PROFILE_SELECTED_STUDENT_ID)
    If selectedStudentIdRange Is Nothing Then
        MsgBox "Benannter Bereich fehlt: " & NAME_PROFILE_SELECTED_STUDENT_ID, vbExclamation, "Navigation"
        Exit Sub
    End If

    Set profileSheet = selectedStudentIdRange.Worksheet
    If profileSheet Is Nothing Then
        MsgBox "Zielblatt fuer benannten Bereich fehlt: " & NAME_PROFILE_SELECTED_STUDENT_ID, vbExclamation, "Navigation"
        Exit Sub
    End If

    selectedStudentIdRange.Value = studentId
    profileSheet.Activate
End Sub

Public Sub OpenClassOverview()
    Dim searchInputRange As Object
    Dim overviewAnchorRange As Object
    Dim overviewSheet As Object

    Set searchInputRange = GetWorkbookNameRange(NAME_CLASS_SEARCH_INPUT)
    If searchInputRange Is Nothing Then
        MsgBox "Benannter Bereich fehlt: " & NAME_CLASS_SEARCH_INPUT, vbExclamation, "Navigation"
        Exit Sub
    End If

    Set overviewAnchorRange = GetWorkbookNameRange(NAME_STUDENT_CARD_PREFIX & "01")
    If overviewAnchorRange Is Nothing Then
        MsgBox "Technischer Anker fehlt: " & NAME_STUDENT_CARD_PREFIX & "01", vbExclamation, "Navigation"
        Exit Sub
    End If

    Set overviewSheet = overviewAnchorRange.Worksheet
    If overviewSheet Is Nothing Then
        MsgBox "Zielblatt fuer Stammgruppenuebersicht fehlt.", vbExclamation, "Navigation"
        Exit Sub
    End If

    ClearUiInputRange searchInputRange
    overviewSheet.Activate
End Sub

Private Sub ClearUiInputRange(ByVal inputRange As Object)
    If inputRange.MergeCells Then
        inputRange.MergeArea.ClearContents
    Else
        inputRange.ClearContents
    End If
End Sub

Private Function ReadCallerShapeName() As String
    If TypeName(Application.Caller) = "String" Then
        ReadCallerShapeName = CStr(Application.Caller)
    End If
End Function

Private Function ReadSlotIdForCardShape(ByVal shapeName As String) As String
    Dim slotId As String

    If Left$(shapeName, Len(SHAPE_STUDENT_CARD_PREFIX)) <> SHAPE_STUDENT_CARD_PREFIX Then Exit Function

    slotId = Mid$(shapeName, Len(SHAPE_STUDENT_CARD_PREFIX) + 1)
    ReadSlotIdForCardShape = slotId
End Function

Private Function ReadStudentIdForSlot(ByVal slotId As String) As String
    Dim studentIdRangeKey As String
    Dim studentIdRange As Object

    If Len(slotId) = 0 Then Exit Function

    studentIdRangeKey = NAME_STUDENT_CARD_ID_PREFIX & slotId
    Set studentIdRange = GetWorkbookNameRange(studentIdRangeKey)
    If studentIdRange Is Nothing Then Exit Function

    ReadStudentIdForSlot = Trim$(CStr(studentIdRange.Value))
End Function

Private Function BuildStudentCardNavigationMessage( _
    ByVal messageText As String, _
    ByVal shapeName As String, _
    ByVal slotId As String, _
    ByVal studentId As String _
) As String
    BuildStudentCardNavigationMessage = _
        messageText & vbCrLf & vbCrLf & _
        "Shape: " & SafeDiagnosticValue(shapeName) & vbCrLf & _
        "Slot: " & SafeDiagnosticValue(slotId) & vbCrLf & _
        "student_id: " & SafeDiagnosticValue(studentId)
End Function

Private Function SafeDiagnosticValue(ByVal diagnosticValue As String) As String
    If Len(diagnosticValue) = 0 Then
        SafeDiagnosticValue = "(leer)"
    Else
        SafeDiagnosticValue = diagnosticValue
    End If
End Function

Private Function GetWorkbookNameRange(ByVal workbookNameKey As String) As Object
    Dim workbookName As Object

    For Each workbookName In ThisWorkbook.Names
        If WorkbookNameMatches(workbookName, workbookNameKey) Then
            Set GetWorkbookNameRange = workbookName.RefersToRange
            Exit Function
        End If
    Next workbookName
End Function

Private Function WorkbookNameMatches(ByVal workbookName As Object, ByVal workbookNameKey As String) As Boolean
    WorkbookNameMatches = (workbookName.Name = workbookNameKey)
End Function

Attribute VB_Name = "UI"
Option Explicit

Public Sub ConfigureStudentCardNavigation()
    Dim overviewSheet As Object
    Dim slotIndex As Long
    Dim anchorRange As Object
    Dim navShape As Object
    Dim shapeName As String

    Set overviewSheet = GetClassOverviewSheet()
    If overviewSheet Is Nothing Then
        MsgBox "Technischer Anker fehlt: " & NAME_STUDENT_CARD_PREFIX & "01", vbExclamation, "Navigation"
        Exit Sub
    End If

    RemoveStudentCardNavigationShapes overviewSheet

    For slotIndex = 1 To STUDENT_CARD_SLOT_COUNT
        Set anchorRange = GetWorkbookNameRange(NAME_STUDENT_CARD_PREFIX & Format$(slotIndex, "00"))
        If anchorRange Is Nothing Then
            MsgBox "Technischer Anker fehlt: " & NAME_STUDENT_CARD_PREFIX & Format$(slotIndex, "00"), vbExclamation, "Navigation"
            Exit Sub
        End If

        shapeName = SHAPE_STUDENT_CARD_PREFIX & Format$(slotIndex, "00")

        Set navShape = overviewSheet.Shapes.AddShape(VBA_SHAPE_TYPE_RECTANGLE, anchorRange.Left, anchorRange.Top, anchorRange.Width, anchorRange.Height)
        With navShape
            .Name = shapeName
            .AlternativeText = "Student card navigation slot " & Format$(slotIndex, "00")
            .OnAction = "OpenStudentProfileFromCard"
            .Placement = VBA_PLACEMENT_MOVE_AND_SIZE
            .Fill.Visible = VBA_OFFICE_TRUE
            .Fill.ForeColor.RGB = RGB(255, 255, 255)
            .Fill.Transparency = 0.99
            .Line.Visible = VBA_OFFICE_FALSE
            .ZOrder VBA_Z_ORDER_BRING_TO_FRONT
        End With
    Next slotIndex
End Sub

Public Sub TestJenaplanVBA()
    MsgBox "Jenaplan VBA Framework läuft.", vbInformation, "Jenaplan"
End Sub

Private Sub RemoveStudentCardNavigationShapes(ByVal overviewSheet As Object)
    Dim slotIndex As Long
    Dim shapeName As String

    For slotIndex = overviewSheet.Shapes.Count To 1 Step -1
        shapeName = overviewSheet.Shapes(slotIndex).Name
        If Left$(shapeName, Len(SHAPE_STUDENT_CARD_PREFIX)) = SHAPE_STUDENT_CARD_PREFIX Then
            overviewSheet.Shapes(slotIndex).Delete
        End If
    Next slotIndex
End Sub

Private Function GetClassOverviewSheet() As Object
    Dim anchorRange As Object

    Set anchorRange = GetWorkbookNameRange(NAME_STUDENT_CARD_PREFIX & "01")
    If anchorRange Is Nothing Then Exit Function

    Set GetClassOverviewSheet = anchorRange.Worksheet
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

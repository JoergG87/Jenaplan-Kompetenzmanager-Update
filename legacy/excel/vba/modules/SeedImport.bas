Attribute VB_Name = "SeedImport"
Option Explicit

Private Const VBEXT_CT_STDMODULE As Long = 1
Private Const VBEXT_CT_MSFORM As Long = 3
Private Const MODULE_GLOBALS As String = "Globals.bas"
Private Const MODULE_NAVIGATION As String = "Navigation.bas"
Private Const MODULE_UI As String = "UI.bas"
Private Const FORM_STUDENT_NEW As String = "frm_student_new.frm"
Private Const FORM_STUDENT_NEW_NAME As String = "frm_student_new"

Public Sub ImportVbaSourcesToSeedFromRepo()
    Dim moduleFolder As String
    Dim formFolder As String

    moduleFolder = ParentFolder(ThisWorkbook.Path) & Application.PathSeparator & _
        "vba" & Application.PathSeparator & "modules"
    formFolder = ParentFolder(ThisWorkbook.Path) & Application.PathSeparator & _
        "vba" & Application.PathSeparator & "forms"

    ImportVbaSourcesToSeed _
        moduleFolder & Application.PathSeparator & MODULE_GLOBALS, _
        moduleFolder & Application.PathSeparator & MODULE_NAVIGATION, _
        moduleFolder & Application.PathSeparator & MODULE_UI

    ImportUserForm FORM_STUDENT_NEW_NAME, formFolder & Application.PathSeparator & FORM_STUDENT_NEW
End Sub

Public Sub ImportVbaSourcesToSeed( _
    ByVal globalsPath As String, _
    ByVal navigationPath As String, _
    ByVal uiPath As String _
)
    ImportStandardModule "Globals", globalsPath
    ImportStandardModule "Navigation", navigationPath
    ImportStandardModule "UI", uiPath
End Sub

Private Sub ImportStandardModule(ByVal moduleName As String, ByVal sourcePath As String)
    Dim project As Object
    Dim existingComponent As Object

    sourcePath = Trim$(sourcePath)
    If Len(sourcePath) = 0 Then
        Err.Raise vbObjectError + 510, "SeedImport", "Quellpfad fehlt fuer Modul: " & moduleName
    End If
    If Len(Dir$(sourcePath)) = 0 Then
        Err.Raise vbObjectError + 511, "SeedImport", "VBA-Quelldatei fehlt: " & sourcePath
    End If

    Set project = GetSeedVbaProject()
    Set existingComponent = FindComponent(project, moduleName)

    If Not existingComponent Is Nothing Then
        If existingComponent.Type <> VBEXT_CT_STDMODULE Then
            Err.Raise vbObjectError + 512, "SeedImport", _
                "Modul ist kein Standardmodul und wird nicht ersetzt: " & moduleName
        End If
        project.VBComponents.Remove existingComponent
    End If

    project.VBComponents.Import sourcePath
End Sub

Private Sub ImportUserForm(ByVal formName As String, ByVal sourcePath As String)
    Dim project As Object
    Dim existingComponent As Object

    sourcePath = Trim$(sourcePath)
    If Len(sourcePath) = 0 Then
        Err.Raise vbObjectError + 515, "SeedImport", "Quellpfad fehlt fuer UserForm: " & formName
    End If
    If Len(Dir$(sourcePath)) = 0 Then
        Err.Raise vbObjectError + 516, "SeedImport", "VBA-UserForm-Datei fehlt: " & sourcePath
    End If

    Set project = GetSeedVbaProject()
    Set existingComponent = FindComponent(project, formName)

    If Not existingComponent Is Nothing Then
        If existingComponent.Type <> VBEXT_CT_MSFORM Then
            Err.Raise vbObjectError + 517, "SeedImport", _
                "Komponente ist keine UserForm und wird nicht ersetzt: " & formName
        End If
        If formName = FORM_STUDENT_NEW_NAME Then
            On Error Resume Next
            ConfigureStudentNewForm existingComponent
            On Error GoTo 0
        End If
        Exit Sub
    End If

    If formName = FORM_STUDENT_NEW_NAME Then
        CreateStudentNewForm project
    Else
        project.VBComponents.Import sourcePath
    End If
End Sub

Private Sub CreateStudentNewForm(ByVal project As Object)
    Dim formComponent As Object

    Set formComponent = project.VBComponents.Add(VBEXT_CT_MSFORM)
    RenameComponent formComponent, FORM_STUDENT_NEW_NAME
    ConfigureStudentNewForm formComponent
End Sub

Private Sub ConfigureStudentNewForm(ByVal formComponent As Object)
    With formComponent
        .Properties("BackColor").Value = &HFCF8F5
        .Properties("Caption").Value = "Neuer Sch" & ChrW$(252) & "ler"
        .Properties("Height").Value = ToPoints(7890)
        .Properties("Width").Value = ToPoints(9720)
        .Properties("StartUpPosition").Value = 1
    End With

    AddLabel formComponent, "ctl_first_name_label", "Vorname *", 600, 540, 4200, 240, 10, True
    AddTextBox formComponent, "ctl_first_name", 600, 780, 8400, 480, 0, False

    AddLabel formComponent, "ctl_last_name_label", "Nachname *", 600, 1320, 4200, 240, 10, True
    AddTextBox formComponent, "ctl_last_name", 600, 1560, 8400, 480, 1, False

    AddLabel formComponent, "ctl_group_id_label", "Stammgruppe *", 600, 2100, 4200, 240, 10, True
    AddComboBox formComponent, "ctl_group_id", 600, 2340, 8400, 480, 2

    AddLabel formComponent, "ctl_course_id_label", "Kurs *", 600, 2880, 4200, 240, 10, True
    AddComboBox formComponent, "ctl_course_id", 600, 3120, 8400, 480, 3

    AddLabel formComponent, "ctl_student_notes_label", "Notiz", 600, 3600, 4200, 240, 10, True
    AddTextBox formComponent, "ctl_student_notes", 600, 3900, 8400, 1260, 4, True

    AddLabel formComponent, "ctl_document_section_label", "Dokumente", 600, 5520, 4200, 300, 12, True
    AddFrame formComponent, "ctl_document_list", 600, 5880, 8400, 480
    AddEmptyStateLabel formComponent, "ctl_document_empty_state", "Noch keine Dokumente vorhanden.", 600, 5960, 8400, 360

    AddButton formComponent, "ctl_add_document", "+ Dokument hinzuf" & ChrW$(252) & "gen", 600, 6480, 3000, 480, 5, False, False
    AddButton formComponent, "ctl_cancel", "Abbrechen", 5400, 6900, 1680, 480, 6, False, True
    AddButton formComponent, "ctl_save", "Speichern", 7200, 6900, 1800, 480, 7, True, False
End Sub

Private Sub RenameComponent(ByVal component As Object, ByVal componentName As String)
    On Error GoTo NamePropertyFallback
    component.Name = componentName
    Exit Sub

NamePropertyFallback:
    Err.Clear
    component.Properties("Name").Value = componentName
End Sub

Private Function AddControl( _
    ByVal formComponent As Object, _
    ByVal programmaticId As String, _
    ByVal controlName As String, _
    ByVal leftValue As Long, _
    ByVal topValue As Long, _
    ByVal widthValue As Long, _
    ByVal heightValue As Long _
) As Object
    Set AddControl = GetOrAddControl(formComponent, programmaticId, controlName)
    With AddControl
        .Left = ToPoints(leftValue)
        .Top = ToPoints(topValue)
        .Width = ToPoints(widthValue)
        .Height = ToPoints(heightValue)
    End With
End Function

Private Function GetOrAddControl( _
    ByVal formComponent As Object, _
    ByVal programmaticId As String, _
    ByVal controlName As String _
) As Object
    On Error Resume Next
    Set GetOrAddControl = formComponent.Designer.Controls(controlName)
    On Error GoTo 0

    If GetOrAddControl Is Nothing Then
        Set GetOrAddControl = formComponent.Designer.Controls.Add(programmaticId, controlName, True)
    End If
End Function

Private Function ToPoints(ByVal twipsValue As Long) As Double
    ToPoints = twipsValue / 20#
End Function

Private Sub ConfigureFont(ByVal control As Object, ByVal sizeValue As Long, ByVal boldValue As Boolean)
    With control.Font
        .Name = "Aptos"
        .Size = sizeValue
        .Bold = boldValue
    End With
End Sub

Private Sub AddLabel( _
    ByVal formComponent As Object, _
    ByVal controlName As String, _
    ByVal captionValue As String, _
    ByVal leftValue As Long, _
    ByVal topValue As Long, _
    ByVal widthValue As Long, _
    ByVal heightValue As Long, _
    ByVal sizeValue As Long, _
    ByVal boldValue As Boolean _
)
    Dim control As Object

    Set control = AddControl(formComponent, "Forms.Label.1", controlName, leftValue, topValue, widthValue, heightValue)
    With control
        .BackStyle = 0
        .Caption = captionValue
        .ForeColor = &H3A3124
        ConfigureFont control, sizeValue, boldValue
    End With
End Sub

Private Sub AddEmptyStateLabel( _
    ByVal formComponent As Object, _
    ByVal controlName As String, _
    ByVal captionValue As String, _
    ByVal leftValue As Long, _
    ByVal topValue As Long, _
    ByVal widthValue As Long, _
    ByVal heightValue As Long _
)
    Dim control As Object

    Set control = AddControl(formComponent, "Forms.Label.1", controlName, leftValue, topValue, widthValue, heightValue)
    With control
        .BackColor = &HF9F6F3
        .Caption = captionValue
        .ForeColor = &H7F7366
        .TextAlign = 2
        ConfigureFont control, 10, False
    End With
End Sub

Private Sub AddTextBox( _
    ByVal formComponent As Object, _
    ByVal controlName As String, _
    ByVal leftValue As Long, _
    ByVal topValue As Long, _
    ByVal widthValue As Long, _
    ByVal heightValue As Long, _
    ByVal tabIndexValue As Long, _
    ByVal multiLineValue As Boolean _
)
    Dim control As Object

    Set control = AddControl(formComponent, "Forms.TextBox.1", controlName, leftValue, topValue, widthValue, heightValue)
    With control
        .BackColor = &HFEFCFB
        .BorderStyle = 1
        .MultiLine = multiLineValue
        On Error Resume Next
        .TabIndex = tabIndexValue
        On Error GoTo 0
        ConfigureFont control, 10, False
    End With
End Sub

Private Sub AddComboBox( _
    ByVal formComponent As Object, _
    ByVal controlName As String, _
    ByVal leftValue As Long, _
    ByVal topValue As Long, _
    ByVal widthValue As Long, _
    ByVal heightValue As Long, _
    ByVal tabIndexValue As Long _
)
    Dim control As Object

    Set control = AddControl(formComponent, "Forms.ComboBox.1", controlName, leftValue, topValue, widthValue, heightValue)
    With control
        .BackColor = &HFEFCFB
        .Style = 2
        On Error Resume Next
        .TabIndex = tabIndexValue
        On Error GoTo 0
        ConfigureFont control, 10, False
    End With
End Sub

Private Sub AddFrame( _
    ByVal formComponent As Object, _
    ByVal controlName As String, _
    ByVal leftValue As Long, _
    ByVal topValue As Long, _
    ByVal widthValue As Long, _
    ByVal heightValue As Long _
)
    Dim control As Object

    Set control = AddControl(formComponent, "Forms.Frame.1", controlName, leftValue, topValue, widthValue, heightValue)
    With control
        .BackColor = &HF9F6F3
        .Caption = vbNullString
        On Error Resume Next
        .TabIndex = 15
        On Error GoTo 0
    End With
End Sub

Private Sub AddButton( _
    ByVal formComponent As Object, _
    ByVal controlName As String, _
    ByVal captionValue As String, _
    ByVal leftValue As Long, _
    ByVal topValue As Long, _
    ByVal widthValue As Long, _
    ByVal heightValue As Long, _
    ByVal tabIndexValue As Long, _
    ByVal defaultValue As Boolean, _
    ByVal cancelValue As Boolean _
)
    Dim control As Object

    Set control = AddControl(formComponent, "Forms.CommandButton.1", controlName, leftValue, topValue, widthValue, heightValue)
    With control
        .BackColor = &HF7F3EF
        .Caption = captionValue
        .ForeColor = &H3A3124
        On Error Resume Next
        .TabIndex = tabIndexValue
        On Error GoTo 0
        If defaultValue Then
            .BackColor = &H505D2F
            .ForeColor = &HFFFFFF
        End If
        ConfigureFont control, 10, True
    End With
End Sub

Private Function ParentFolder(ByVal folderPath As String) As String
    Dim separatorPosition As Long

    separatorPosition = InStrRev(folderPath, Application.PathSeparator)
    If separatorPosition = 0 Then
        Err.Raise vbObjectError + 514, "SeedImport", _
            "Seed-Verzeichnis kann nicht ausgewertet werden: " & folderPath
    End If

    ParentFolder = Left$(folderPath, separatorPosition - 1)
End Function

Private Function GetSeedVbaProject() As Object
    On Error GoTo AccessDenied
    Set GetSeedVbaProject = ThisWorkbook.VBProject
    Exit Function

AccessDenied:
    Err.Raise vbObjectError + 513, "SeedImport", _
        "Excel blockiert den Zugriff auf ThisWorkbook.VBProject. " & _
        "Bitte in Excel den vertrauenswuerdigen Zugriff auf das VBA-Projektobjektmodell aktivieren " & _
        "und den Seed erneut speichern. Originalfehler: " & Err.Number & " - " & Err.Description
End Function

Private Function FindComponent(ByVal project As Object, ByVal componentName As String) As Object
    Dim component As Object

    For Each component In project.VBComponents
        If component.Name = componentName Then
            Set FindComponent = component
            Exit Function
        End If
    Next component
End Function

Attribute VB_Name = "UI"
Option Explicit

Private Const STUDENT_DIALOG_TEST_WIDTH As Double = 500
Private Const STUDENT_DIALOG_TEST_HEIGHT As Double = 600
Private Const DIALOG_NEW_STUDENT_SHEET_NAME As String = "dlg_neuer_schueler"
Private Const RUNTIME_DIAGNOSTIC_LOG_FILE_NAME As String = "runtime_adapter_diagnostic.log"
Private Const RUNTIME_STDOUT_LOG_FILE_NAME As String = "runtime_python_stdout.log"
Private Const RUNTIME_STDERR_LOG_FILE_NAME As String = "runtime_python_stderr.log"
Private Const RUNTIME_EXIT_CODE_FILE_NAME As String = "runtime_python_exit_code.txt"
Private Const RUNTIME_COMMAND_SCRIPT_FILE_NAME As String = "runtime_python_command.zsh"

Private mRuntimeDiagnosticStep As String
Private mRuntimePythonStarted As Boolean

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

    ConfigureProfileBackNavigation
    ConfigureNewStudentDialogActions
End Sub

Public Sub TestJenaplanVBA()
    MsgBox "Jenaplan VBA Framework läuft.", vbInformation, "Jenaplan"
End Sub

Public Sub OpenNewStudentDialog()
    On Error GoTo DialogOpenFailed
    DisableStudentDialogFocusTargets frm_student_new
    ResizeStudentDialogForMacTest frm_student_new
    frm_student_new.Show vbModeless
    Exit Sub

DialogOpenFailed:
    MsgBox "Der Dialog konnte nicht angezeigt werden: " & Err.Description, vbExclamation, "Neuer Schüler"
End Sub

Public Sub SaveNewStudentDialog()
    On Error GoTo RuntimeFailed

    ResetRuntimeDiagnostic
    SetRuntimeDiagnosticStep "SaveNewStudentDialog: Start"

    Dim commandPath As String
    Dim resultPath As String
    Dim databasePath As String
    Dim commandJson As String
    Dim resultJson As String

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: Named Ranges pruefen"
    ValidateNewStudentDialogRanges

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: Runtime-Pfade bestimmen"
    commandPath = RuntimeArtifactPath(RUNTIME_COMMAND_FILE_NAME)
    resultPath = RuntimeArtifactPath(RUNTIME_RESULT_FILE_NAME)
    databasePath = ProjectRootPath() & "/" & RUNTIME_DATABASE_RELATIVE_PATH
    AppendRuntimeDiagnostic "commandPath=" & commandPath
    AppendRuntimeDiagnostic "resultPath=" & resultPath
    AppendRuntimeDiagnostic "databasePath=" & databasePath

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: CreateStudentCommand JSON bauen"
    commandJson = BuildCreateStudentCommandJson()

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: alte Ergebnisdatei loeschen"
    DeleteFileIfExists resultPath

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: runtime_command.json schreiben"
    WriteTextFile commandPath, commandJson
    AppendRuntimeDiagnostic "runtime_command.json geschrieben"

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: Python Runtime starten"
    StartPythonRuntime commandPath, resultPath, databasePath

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: runtime_result.json abwarten"
    resultJson = WaitForRuntimeResult(resultPath, 30)

    SetRuntimeDiagnosticStep "SaveNewStudentDialog: Runtime-Ergebnis auswerten"
    If RuntimeResultSucceeded(resultJson) Then
        AppendRuntimeDiagnostic "Runtime-Ergebnis: success=true"
        MsgBox RuntimeResultMessage(resultJson, "Schueler wurde in SQLite gespeichert."), vbInformation, "Neuer Schueler"
    Else
        AppendRuntimeDiagnostic "Runtime-Ergebnis: success=false"
        MsgBox RuntimeResultMessage(resultJson, "Der Schueler konnte nicht gespeichert werden."), vbExclamation, "Neuer Schueler"
    End If
    Exit Sub

RuntimeFailed:
    Dim errorNumber As Long
    Dim errorDescription As String
    Dim errorSource As String

    errorNumber = Err.Number
    errorDescription = Err.Description
    errorSource = Err.Source
    AppendRuntimeDiagnostic "FEHLER Schritt=" & mRuntimeDiagnosticStep & "; Err.Number=" & CStr(errorNumber) & "; Err.Description=" & errorDescription & "; Err.Source=" & errorSource & "; PythonStarted=" & CStr(mRuntimePythonStarted)

    MsgBox _
        "Der Speichervorgang konnte nicht gestartet werden." & vbCrLf & vbCrLf & _
        "Diagnose-Schritt: " & mRuntimeDiagnosticStep & vbCrLf & _
        "Err.Number: " & CStr(errorNumber) & vbCrLf & _
        "Err.Description: " & errorDescription & vbCrLf & _
        "Err.Source: " & errorSource & vbCrLf & _
        "Python gestartet: " & IIf(mRuntimePythonStarted, "Ja", "Nein") & vbCrLf & _
        "Diagnose-Log: " & RuntimeArtifactPath(RUNTIME_DIAGNOSTIC_LOG_FILE_NAME), _
        vbExclamation, _
        "Neuer Schueler"
End Sub

Private Sub DisableStudentDialogFocusTargets(ByVal studentDialog As Object)
    Dim control As Object

    For Each control In studentDialog.Controls
        On Error Resume Next
        control.TabStop = False
        control.TakeFocusOnClick = False
        On Error GoTo 0
    Next control
End Sub

Private Sub ResizeStudentDialogForMacTest(ByVal studentDialog As Object)
    On Error Resume Next
    studentDialog.Width = STUDENT_DIALOG_TEST_WIDTH
    studentDialog.Height = STUDENT_DIALOG_TEST_HEIGHT
    On Error GoTo 0
End Sub

Private Sub ConfigureNewStudentDialogActions()
    Dim anchorRange As Object
    Dim dialogSheet As Object
    Dim saveShape As Object

    Set anchorRange = GetWorkbookNameRange(NAME_DIALOG_NEW_STUDENT_SAVE)
    If anchorRange Is Nothing Then
        MsgBox "Technischer Anker fehlt: " & NAME_DIALOG_NEW_STUDENT_SAVE, vbExclamation, "Neuer Schueler"
        Exit Sub
    End If

    Set dialogSheet = anchorRange.Worksheet
    If dialogSheet Is Nothing Then
        MsgBox "Zielblatt fuer Neuer-Schueler-Dialog fehlt.", vbExclamation, "Neuer Schueler"
        Exit Sub
    End If

    dialogSheet.Unprotect
    RemoveShapeByName dialogSheet, SHAPE_DIALOG_NEW_STUDENT_SAVE

    Set saveShape = dialogSheet.Shapes.AddShape(VBA_SHAPE_TYPE_RECTANGLE, anchorRange.Left, anchorRange.Top, anchorRange.Width, anchorRange.Height)
    With saveShape
        .Name = SHAPE_DIALOG_NEW_STUDENT_SAVE
        .AlternativeText = "Save new student"
        .OnAction = "SaveNewStudentDialog"
        .Placement = VBA_PLACEMENT_MOVE_AND_SIZE
        .Fill.Visible = VBA_OFFICE_TRUE
        .Fill.ForeColor.RGB = RGB(31, 97, 78)
        .Fill.Transparency = 0.99
        .Line.Visible = VBA_OFFICE_FALSE
        .ZOrder VBA_Z_ORDER_BRING_TO_FRONT
    End With

    dialogSheet.Protect DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    dialogSheet.EnableSelection = VBA_ENABLE_SELECTION_UNLOCKED_CELLS
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

Private Sub ConfigureProfileBackNavigation()
    Dim anchorRange As Object
    Dim profileSheet As Object
    Dim navShape As Object

    Set anchorRange = GetWorkbookNameRange(NAME_PROFILE_BACK_TO_CLASS_OVERVIEW)
    If anchorRange Is Nothing Then
        MsgBox "Technischer Anker fehlt: " & NAME_PROFILE_BACK_TO_CLASS_OVERVIEW, vbExclamation, "Navigation"
        Exit Sub
    End If

    Set profileSheet = anchorRange.Worksheet
    RemoveProfileBackNavigationShape profileSheet

    Set navShape = profileSheet.Shapes.AddShape(VBA_SHAPE_TYPE_RECTANGLE, anchorRange.Left, anchorRange.Top, anchorRange.Width, anchorRange.Height)
    With navShape
        .Name = SHAPE_PROFILE_BACK_PREFIX
        .AlternativeText = "Profile back navigation"
        .OnAction = "OpenClassOverview"
        .Placement = VBA_PLACEMENT_MOVE_AND_SIZE
        .Fill.Visible = VBA_OFFICE_TRUE
        .Fill.ForeColor.RGB = RGB(255, 255, 255)
        .Fill.Transparency = 0.99
        .Line.Visible = VBA_OFFICE_FALSE
        .ZOrder VBA_Z_ORDER_BRING_TO_FRONT
    End With
End Sub

Private Sub RemoveProfileBackNavigationShape(ByVal profileSheet As Object)
    Dim slotIndex As Long
    Dim shapeName As String

    For slotIndex = profileSheet.Shapes.Count To 1 Step -1
        shapeName = profileSheet.Shapes(slotIndex).Name
        If shapeName = SHAPE_PROFILE_BACK_PREFIX Then
            profileSheet.Shapes(slotIndex).Delete
        End If
    Next slotIndex
End Sub

Private Sub RemoveShapeByName(ByVal targetSheet As Object, ByVal targetShapeName As String)
    Dim shapeIndex As Long

    For shapeIndex = targetSheet.Shapes.Count To 1 Step -1
        If targetSheet.Shapes(shapeIndex).Name = targetShapeName Then
            targetSheet.Shapes(shapeIndex).Delete
        End If
    Next shapeIndex
End Sub

Private Sub ValidateNewStudentDialogRanges()
    ValidateNewStudentDialogRange NAME_DIALOG_NEW_STUDENT_FIRST_NAME
    ValidateNewStudentDialogRange NAME_DIALOG_NEW_STUDENT_LAST_NAME
    ValidateNewStudentDialogRange NAME_DIALOG_NEW_STUDENT_GROUP
    ValidateNewStudentDialogRange NAME_DIALOG_NEW_STUDENT_COURSE
    ValidateNewStudentDialogRange NAME_DIALOG_NEW_STUDENT_NOTES
    ValidateNewStudentDialogRange NAME_DIALOG_NEW_STUDENT_SAVE
End Sub

Private Sub ValidateNewStudentDialogRange(ByVal workbookNameKey As String)
    Dim namedRange As Object
    Dim worksheetName As String

    SetRuntimeDiagnosticStep "ValidateNewStudentDialogRange: " & workbookNameKey
    Set namedRange = GetWorkbookNameRange(workbookNameKey)
    If namedRange Is Nothing Then
        Err.Raise vbObjectError + 520, "ValidateNewStudentDialogRange", "Benannter Bereich fehlt: " & workbookNameKey
    End If

    worksheetName = namedRange.Worksheet.Name
    AppendRuntimeDiagnostic workbookNameKey & " gefunden auf Blatt " & worksheetName & " in " & namedRange.Address(False, False)
    If worksheetName <> DIALOG_NEW_STUDENT_SHEET_NAME Then
        Err.Raise vbObjectError + 521, "ValidateNewStudentDialogRange", "Benannter Bereich liegt auf falschem Blatt: " & workbookNameKey & " -> " & worksheetName
    End If
End Sub

Private Function BuildCreateStudentCommandJson() As String
    SetRuntimeDiagnosticStep "BuildCreateStudentCommandJson: Start"
    BuildCreateStudentCommandJson = _
        "{" & _
        JsonProperty("command", "student.create") & "," & _
        JsonObjectProperty( _
            "data", _
            JsonProperty("first_name", ReadNamedRangeText(NAME_DIALOG_NEW_STUDENT_FIRST_NAME)) & "," & _
            JsonProperty("last_name", ReadNamedRangeText(NAME_DIALOG_NEW_STUDENT_LAST_NAME)) & "," & _
            JsonProperty("group", ReadNamedRangeText(NAME_DIALOG_NEW_STUDENT_GROUP)) & "," & _
            JsonProperty("course", ReadNamedRangeText(NAME_DIALOG_NEW_STUDENT_COURSE)) & "," & _
            JsonProperty("student_notes", ReadNamedRangeText(NAME_DIALOG_NEW_STUDENT_NOTES)) _
        ) & _
        "}"
End Function

Private Function ReadNamedRangeText(ByVal workbookNameKey As String) As String
    Dim namedRange As Object
    Dim valueCell As Object

    SetRuntimeDiagnosticStep "ReadNamedRangeText: Named Range suchen " & workbookNameKey
    Set namedRange = GetWorkbookNameRange(workbookNameKey)
    If namedRange Is Nothing Then
        Err.Raise vbObjectError + 514, "ReadNamedRangeText", "Benannter Bereich fehlt: " & workbookNameKey
    End If

    AppendRuntimeDiagnostic workbookNameKey & " Leseadresse=" & namedRange.Worksheet.Name & "!" & namedRange.Address(False, False) & "; MergeCells=" & CStr(namedRange.MergeCells)
    SetRuntimeDiagnosticStep "ReadNamedRangeText: erste Zelle lesen " & workbookNameKey
    Set valueCell = namedRange.Cells(1, 1)

    SetRuntimeDiagnosticStep "ReadNamedRangeText: Zellwert lesen " & workbookNameKey
    ReadNamedRangeText = Trim$(CStr(valueCell.Value))
    AppendRuntimeDiagnostic workbookNameKey & " Wertlaenge=" & CStr(Len(ReadNamedRangeText))
End Function

Private Function JsonObjectProperty(ByVal propertyName As String, ByVal objectJson As String) As String
    JsonObjectProperty = QuoteJson(propertyName) & ":{" & objectJson & "}"
End Function

Private Function JsonRawProperty(ByVal propertyName As String, ByVal rawValue As String) As String
    JsonRawProperty = QuoteJson(propertyName) & ":" & rawValue
End Function

Private Function JsonProperty(ByVal propertyName As String, ByVal propertyValue As String) As String
    JsonProperty = QuoteJson(propertyName) & ":" & QuoteJson(propertyValue)
End Function

Private Function QuoteJson(ByVal plainText As String) As String
    QuoteJson = Chr$(34) & EscapeJson(plainText) & Chr$(34)
End Function

Private Function EscapeJson(ByVal plainText As String) As String
    Dim escapedText As String

    escapedText = Replace(plainText, "\", "\\")
    escapedText = Replace(escapedText, Chr$(34), Chr$(92) & Chr$(34))
    escapedText = Replace(escapedText, vbCrLf, "\n")
    escapedText = Replace(escapedText, vbCr, "\n")
    escapedText = Replace(escapedText, vbLf, "\n")
    EscapeJson = escapedText
End Function

Private Sub StartPythonRuntime(ByVal commandPath As String, ByVal resultPath As String, ByVal databasePath As String)
    Dim commandLine As String
    Dim shellScript As String
    Dim shellCommand As String
    Dim macScriptText As String
    Dim macScriptResult As String
    Dim projectPath As String
    Dim stdoutPath As String
    Dim stderrPath As String
    Dim exitCodePath As String
    Dim scriptPath As String

    SetRuntimeDiagnosticStep "StartPythonRuntime: Kommandozeile bauen"
    projectPath = ProjectRootPath()
    stdoutPath = RuntimeArtifactPath(RUNTIME_STDOUT_LOG_FILE_NAME)
    stderrPath = RuntimeArtifactPath(RUNTIME_STDERR_LOG_FILE_NAME)
    exitCodePath = RuntimeArtifactPath(RUNTIME_EXIT_CODE_FILE_NAME)
    scriptPath = RuntimeArtifactPath(RUNTIME_COMMAND_SCRIPT_FILE_NAME)
    DeleteFileIfExists stdoutPath
    DeleteFileIfExists stderrPath
    DeleteFileIfExists exitCodePath
    DeleteFileIfExists scriptPath

    commandLine = _
        "cd " & ShellQuote(projectPath) & _
        " && /usr/bin/env python3 " & _
        ShellQuote(projectPath & "/km.py") & _
        " --database " & ShellQuote(databasePath) & _
        " --result-file " & ShellQuote(resultPath) & _
        " student create --command-file " & ShellQuote(commandPath)

    shellScript = _
        "#!/bin/zsh" & vbLf & _
        "cd " & ShellQuote(projectPath) & " || exit_code=$?" & vbLf & _
        "if [ -z ""${exit_code:-}"" ]; then" & vbLf & _
        "  /usr/bin/env python3 " & ShellQuote(projectPath & "/km.py") & _
        " --database " & ShellQuote(databasePath) & _
        " --result-file " & ShellQuote(resultPath) & _
        " student create --command-file " & ShellQuote(commandPath) & _
        " > " & ShellQuote(stdoutPath) & _
        " 2> " & ShellQuote(stderrPath) & vbLf & _
        "  exit_code=$?" & vbLf & _
        "fi" & vbLf & _
        "printf '%s\n' ""$exit_code"" > " & ShellQuote(exitCodePath) & vbLf & _
        "if [ ! -f " & ShellQuote(resultPath) & " ]; then" & vbLf & _
        "  printf '%s\n' " & ShellQuote(RuntimeStartErrorJson()) & " > " & ShellQuote(resultPath) & vbLf & _
        "fi" & vbLf

    WriteTextFile scriptPath, shellScript

    shellCommand = "/bin/zsh " & ShellQuote(scriptPath)

    AppendRuntimeDiagnostic "Python commandLine=" & commandLine
    AppendRuntimeDiagnostic "runtime_python_command.zsh geschrieben=" & scriptPath
    AppendRuntimeDiagnostic "Shell script path=" & scriptPath
    AppendRuntimeDiagnostic "Shell command=" & shellCommand
    AppendRuntimeDiagnostic "stdoutLogPath=" & stdoutPath
    AppendRuntimeDiagnostic "stderrLogPath=" & stderrPath
    AppendRuntimeDiagnostic "exitCodePath=" & exitCodePath

    SetRuntimeDiagnosticStep "StartPythonRuntime: MacScript do shell script aufrufen"
    macScriptText = "do shell script " & AppleScriptQuote(shellCommand)
    AppendRuntimeDiagnostic "MacScript do shell script verwendet"
    AppendRuntimeDiagnostic "MacScript=" & macScriptText
    macScriptResult = MacScript(macScriptText)
    mRuntimePythonStarted = True
    AppendRuntimeDiagnostic "MacScript abgeschlossen; Rueckgabewertlaenge=" & CStr(Len(macScriptResult))
    AppendRuntimeDiagnostic "runtime_result vorhanden nach MacScript=" & CStr(FileExists(resultPath))
    AppendRuntimeDiagnostic "stdout vorhanden nach MacScript=" & CStr(FileExists(stdoutPath))
    AppendRuntimeDiagnostic "stderr vorhanden nach MacScript=" & CStr(FileExists(stderrPath))
    AppendRuntimeDiagnostic "exitcode vorhanden nach MacScript=" & CStr(FileExists(exitCodePath))
End Sub

Private Function WaitForRuntimeResult(ByVal resultPath As String, ByVal timeoutSeconds As Long) As String
    Dim startTime As Single

    SetRuntimeDiagnosticStep "WaitForRuntimeResult: Warten auf " & resultPath
    startTime = Timer
    Do While Not FileExists(resultPath)
        DoEvents
        If Timer - startTime > timeoutSeconds Then
            AppendRuntimeDiagnostic "runtime_result vorhanden=Nein"
            Err.Raise vbObjectError + 515, "WaitForRuntimeResult", "Python Runtime hat keine Ergebnisdatei erzeugt."
        End If
    Loop

    AppendRuntimeDiagnostic "runtime_result vorhanden=Ja"
    SetRuntimeDiagnosticStep "WaitForRuntimeResult: Ergebnisdatei lesen"
    WaitForRuntimeResult = ReadTextFile(resultPath)
    AppendRuntimeDiagnostic "runtime_result.json gelesen; Laenge=" & CStr(Len(WaitForRuntimeResult))
End Function

Private Function RuntimeStartErrorJson() As String
    RuntimeStartErrorJson = _
        "{" & _
        JsonRawProperty("success", "false") & "," & _
        JsonProperty("command_name", "student.create") & "," & _
        JsonProperty("error_type", "RuntimeStartError") & "," & _
        JsonProperty("message", "Python Runtime hat keine Ergebnisdatei erzeugt. Details siehe runtime_python_stderr.log.") & _
        "}"
End Function

Private Function RuntimeResultSucceeded(ByVal resultJson As String) As Boolean
    RuntimeResultSucceeded = (InStr(1, resultJson, """success"": true", vbTextCompare) > 0)
End Function

Private Function RuntimeResultMessage(ByVal resultJson As String, ByVal fallbackMessage As String) As String
    Dim messageText As String
    Dim studentId As String

    messageText = JsonStringValue(resultJson, "message")
    studentId = JsonStringValue(resultJson, "student_id")

    If Len(messageText) = 0 Then messageText = fallbackMessage
    If Len(studentId) > 0 Then messageText = messageText & vbCrLf & "student_id: " & studentId

    RuntimeResultMessage = messageText
End Function

Private Function JsonStringValue(ByVal resultJson As String, ByVal propertyName As String) As String
    Dim propertyToken As String
    Dim valueStart As Long
    Dim valueEnd As Long

    propertyToken = """" & propertyName & """: """
    valueStart = InStr(1, resultJson, propertyToken, vbTextCompare)
    If valueStart = 0 Then Exit Function

    valueStart = valueStart + Len(propertyToken)
    valueEnd = InStr(valueStart, resultJson, """")
    If valueEnd = 0 Then Exit Function

    JsonStringValue = Mid$(resultJson, valueStart, valueEnd - valueStart)
End Function

Private Function RuntimeArtifactPath(ByVal fileName As String) As String
    RuntimeArtifactPath = ThisWorkbook.Path & "/" & fileName
End Function

Private Sub ResetRuntimeDiagnostic()
    mRuntimeDiagnosticStep = "(nicht gestartet)"
    mRuntimePythonStarted = False
    DeleteFileIfExists RuntimeArtifactPath(RUNTIME_DIAGNOSTIC_LOG_FILE_NAME)
    AppendRuntimeDiagnostic "Diagnose gestartet"
End Sub

Private Sub SetRuntimeDiagnosticStep(ByVal stepText As String)
    mRuntimeDiagnosticStep = stepText
    AppendRuntimeDiagnostic "STEP " & stepText
End Sub

Private Sub AppendRuntimeDiagnostic(ByVal messageText As String)
    On Error Resume Next

    Dim fileNumber As Integer

    fileNumber = FreeFile
    Open RuntimeArtifactPath(RUNTIME_DIAGNOSTIC_LOG_FILE_NAME) For Append As #fileNumber
    Print #fileNumber, Format$(Now, "yyyy-mm-dd hh:nn:ss") & " | " & messageText
    Close #fileNumber
End Sub

Private Function ProjectRootPath() As String
    Dim workbookPath As String

    workbookPath = ThisWorkbook.Path
    If Right$(workbookPath, 7) = "/output" Or Right$(workbookPath, 6) = "/seeds" Then
        ProjectRootPath = Left$(workbookPath, InStrRev(workbookPath, "/") - 1)
    Else
        ProjectRootPath = workbookPath
    End If
End Function

Private Function ShellQuote(ByVal pathText As String) As String
    ShellQuote = "'" & Replace(pathText, "'", "'\''") & "'"
End Function

Private Function AppleScriptQuote(ByVal plainText As String) As String
    AppleScriptQuote = Chr$(34) & Replace(Replace(plainText, "\", "\\"), Chr$(34), "\" & Chr$(34)) & Chr$(34)
End Function

Private Sub WriteTextFile(ByVal targetPath As String, ByVal textContent As String)
    Dim fileNumber As Integer

    fileNumber = FreeFile
    Open targetPath For Output As #fileNumber
    Print #fileNumber, textContent
    Close #fileNumber
End Sub

Private Function ReadTextFile(ByVal sourcePath As String) As String
    Dim fileNumber As Integer

    fileNumber = FreeFile
    Open sourcePath For Binary Access Read As #fileNumber
    ReadTextFile = Space$(LOF(fileNumber))
    Get #fileNumber, , ReadTextFile
    Close #fileNumber
End Function

Private Sub DeleteFileIfExists(ByVal targetPath As String)
    If FileExists(targetPath) Then Kill targetPath
End Sub

Private Function FileExists(ByVal targetPath As String) As Boolean
    FileExists = (Len(Dir$(targetPath)) > 0)
End Function

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

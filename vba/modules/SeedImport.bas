Attribute VB_Name = "SeedImport"
Option Explicit

Private Const VBEXT_CT_STDMODULE As Long = 1
Private Const MODULE_GLOBALS As String = "Globals.bas"
Private Const MODULE_NAVIGATION As String = "Navigation.bas"
Private Const MODULE_UI As String = "UI.bas"

Public Sub ImportVbaSourcesToSeedFromRepo()
    Dim moduleFolder As String

    moduleFolder = ParentFolder(ThisWorkbook.Path) & Application.PathSeparator & _
        "vba" & Application.PathSeparator & "modules"

    ImportVbaSourcesToSeed _
        moduleFolder & Application.PathSeparator & MODULE_GLOBALS, _
        moduleFolder & Application.PathSeparator & MODULE_NAVIGATION, _
        moduleFolder & Application.PathSeparator & MODULE_UI
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

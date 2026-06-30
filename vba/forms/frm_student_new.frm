VERSION 5.00
Begin VB.UserForm frm_student_new
   BackColor       =   &H00F7F5F2&
   Caption         =   "Neuer Schüler"
   ClientHeight    =   6720
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   5760
   StartUpPosition =   1
   Begin MSForms.CommandButton ctl_save
      Caption         =   "Speichern"
      Default         =   -1  'True
      Height          =   360
      Left            =   4200
      TabIndex        =   7
      Top             =   6000
      Width           =   1080
   End
   Begin MSForms.CommandButton ctl_cancel
      Cancel          =   -1  'True
      Caption         =   "Abbrechen"
      Height          =   360
      Left            =   3000
      TabIndex        =   6
      Top             =   6000
      Width           =   1080
   End
   Begin MSForms.CommandButton ctl_add_document
      Caption         =   "+ Dokument hinzufügen"
      Height          =   360
      Left            =   480
      TabIndex        =   5
      Top             =   5200
      Width           =   2040
   End
   Begin MSForms.Frame ctl_document_list
      BackColor       =   &H00FFFFFF&
      Caption         =   ""
      Height          =   420
      Left            =   480
      TabIndex        =   15
      Top             =   4660
      Width           =   4800
   End
   Begin MSForms.Label ctl_document_empty_state
      BackColor       =   &H00FFFFFF&
      Caption         =   "Noch keine Dokumente ausgewählt."
      ForeColor       =   &H006F6760&
      Height          =   360
      Left            =   720
      TabIndex        =   14
      Top             =   4740
      Width           =   4200
   End
   Begin MSForms.Label ctl_document_section_label
      BackStyle       =   0
      Caption         =   "Dokumente"
      ForeColor       =   &H0038322C&
      Height          =   240
      Left            =   480
      TabIndex        =   13
      Top             =   4380
      Width           =   4200
   End
   Begin MSForms.TextBox ctl_student_notes
      Height          =   900
      Left            =   480
      MultiLine       =   -1
      TabIndex        =   4
      Top             =   3360
      Width           =   4800
   End
   Begin MSForms.Label ctl_student_notes_label
      BackStyle       =   0
      Caption         =   "Notiz"
      ForeColor       =   &H0038322C&
      Height          =   240
      Left            =   480
      TabIndex        =   12
      Top             =   3060
      Width           =   4200
   End
   Begin MSForms.ComboBox ctl_course_id
      Height          =   300
      Left            =   480
      Style           =   2
      TabIndex        =   3
      Top             =   2620
      Width           =   4800
   End
   Begin MSForms.Label ctl_course_id_label
      BackStyle       =   0
      Caption         =   "Kurs *"
      ForeColor       =   &H0038322C&
      Height          =   240
      Left            =   480
      TabIndex        =   11
      Top             =   2320
      Width           =   4200
   End
   Begin MSForms.ComboBox ctl_group_id
      Height          =   300
      Left            =   480
      Style           =   2
      TabIndex        =   2
      Top             =   1940
      Width           =   4800
   End
   Begin MSForms.Label ctl_group_id_label
      BackStyle       =   0
      Caption         =   "Stammgruppe *"
      ForeColor       =   &H0038322C&
      Height          =   240
      Left            =   480
      TabIndex        =   10
      Top             =   1640
      Width           =   4200
   End
   Begin MSForms.TextBox ctl_last_name
      Height          =   300
      Left            =   480
      TabIndex        =   1
      Top             =   1260
      Width           =   4800
   End
   Begin MSForms.Label ctl_last_name_label
      BackStyle       =   0
      Caption         =   "Nachname *"
      ForeColor       =   &H0038322C&
      Height          =   240
      Left            =   480
      TabIndex        =   9
      Top             =   960
      Width           =   4200
   End
   Begin MSForms.TextBox ctl_first_name
      Height          =   300
      Left            =   480
      TabIndex        =   0
      Top             =   580
      Width           =   4800
   End
   Begin MSForms.Label ctl_first_name_label
      BackStyle       =   0
      Caption         =   "Vorname *"
      ForeColor       =   &H0038322C&
      Height          =   240
      Left            =   480
      TabIndex        =   8
      Top             =   280
      Width           =   4200
   End
End
Attribute VB_Name = "frm_student_new"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False

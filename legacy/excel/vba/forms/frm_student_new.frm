VERSION 5.00
Begin VB.UserForm frm_student_new
   BackColor       =   &H00FCF8F5&
   Caption         =   "Neuer Schüler"
   ClientHeight    =   7560
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   9600
   StartUpPosition =   1
   Begin MSForms.CommandButton ctl_save
      BackColor       =   &H00505D2F&
      Caption         =   "Speichern"
      Default         =   -1  'True
      ForeColor       =   &H00FFFFFF&
      Height          =   480
      Left            =   7200
      TabIndex        =   7
      Top             =   6900
      Width           =   1800
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.CommandButton ctl_cancel
      BackColor       =   &H00F7F3EF&
      Cancel          =   -1  'True
      Caption         =   "Abbrechen"
      ForeColor       =   &H003A3124&
      Height          =   480
      Left            =   5400
      TabIndex        =   6
      Top             =   6900
      Width           =   1680
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.CommandButton ctl_add_document
      BackColor       =   &H00F7F3EF&
      Caption         =   "+ Dokument hinzufügen"
      ForeColor       =   &H003A3124&
      Height          =   480
      Left            =   600
      TabIndex        =   5
      Top             =   6480
      Width           =   3000
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.Frame ctl_document_list
      BackColor       =   &H00F9F6F3&
      Caption         =   ""
      Height          =   480
      Left            =   600
      TabIndex        =   15
      Top             =   5880
      Width           =   8400
   End
   Begin MSForms.Label ctl_document_empty_state
      BackColor       =   &H00F9F6F3&
      Caption         =   "Noch keine Dokumente vorhanden."
      ForeColor       =   &H007F7366&
      Height          =   360
      Left            =   600
      TabIndex        =   14
      TextAlign       =   2
      Top             =   5960
      Width           =   8400
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.Label ctl_document_section_label
      BackStyle       =   0
      Caption         =   "Dokumente"
      ForeColor       =   &H003A3124&
      Height          =   300
      Left            =   600
      TabIndex        =   13
      Top             =   5520
      Width           =   4200
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.TextBox ctl_student_notes
      BackColor       =   &H00FEFCFB&
      BorderStyle     =   1
      Height          =   1260
      Left            =   600
      MultiLine       =   -1
      TabIndex        =   4
      Top             =   3900
      Width           =   8400
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.Label ctl_student_notes_label
      BackStyle       =   0
      Caption         =   "Notiz"
      ForeColor       =   &H003A3124&
      Height          =   240
      Left            =   600
      TabIndex        =   12
      Top             =   3600
      Width           =   4200
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.ComboBox ctl_course_id
      BackColor       =   &H00FEFCFB&
      Height          =   480
      Left            =   600
      Style           =   2
      TabIndex        =   3
      Top             =   3120
      Width           =   8400
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.Label ctl_course_id_label
      BackStyle       =   0
      Caption         =   "Kurs *"
      ForeColor       =   &H003A3124&
      Height          =   240
      Left            =   600
      TabIndex        =   11
      Top             =   2880
      Width           =   4200
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.ComboBox ctl_group_id
      BackColor       =   &H00FEFCFB&
      Height          =   480
      Left            =   600
      Style           =   2
      TabIndex        =   2
      Top             =   2340
      Width           =   8400
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.Label ctl_group_id_label
      BackStyle       =   0
      Caption         =   "Stammgruppe *"
      ForeColor       =   &H003A3124&
      Height          =   240
      Left            =   600
      TabIndex        =   10
      Top             =   2100
      Width           =   4200
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.TextBox ctl_last_name
      BackColor       =   &H00FEFCFB&
      BorderStyle     =   1
      Height          =   480
      Left            =   600
      TabIndex        =   1
      Top             =   1560
      Width           =   8400
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.Label ctl_last_name_label
      BackStyle       =   0
      Caption         =   "Nachname *"
      ForeColor       =   &H003A3124&
      Height          =   240
      Left            =   600
      TabIndex        =   9
      Top             =   1320
      Width           =   4200
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.TextBox ctl_first_name
      BackColor       =   &H00FEFCFB&
      BorderStyle     =   1
      Height          =   480
      Left            =   600
      TabIndex        =   0
      Top             =   780
      Width           =   8400
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
   Begin MSForms.Label ctl_first_name_label
      BackStyle       =   0
      Caption         =   "Vorname *"
      ForeColor       =   &H003A3124&
      Height          =   240
      Left            =   600
      TabIndex        =   8
      Top             =   540
      Width           =   4200
      BeginProperty Font
         Name            =   "Aptos"
         Size            =   10
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
   End
End
Attribute VB_Name = "frm_student_new"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False

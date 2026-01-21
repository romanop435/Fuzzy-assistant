; Inno Setup installer script for Fazi Assistant

#define AppName "Fazzy Assistant"
#define AppVersion "1.0.0"
#define AppPublisher "Fazi"
#define AppExeName "FaziAssistant.exe"

[Setup]
AppId={{8B0C6E1B-7DEB-4B82-AE7F-54F991B6E9D6}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\FaziAssistant
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=FaziAssistantSetup
SetupIconFile=..\assets\logo-fuzzy.ico
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
#if DirExists("..\models")
Source: "..\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Run {#AppName}"; Flags: nowait postinstall skipifsilent

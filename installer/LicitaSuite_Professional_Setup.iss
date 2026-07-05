#define MyAppName "LicitaSuite"
#define MyAppVersion "6.1"
#define MyAppPublisher "LicitaSuite"
#define MyAppExeName "LicitaSuite.exe"

[Setup]
AppId={{A5BFB0D1-4E42-4B20-8A17-LICITASUITE610FINAL}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} 6.1 Professional FINAL
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\LicitaSuite
DefaultGroupName=LicitaSuite
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=LicitaSuite_6_1_Professional_FINAL_Setup
SetupIconFile=..\assets\LicitaSuite.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Files]
Source: "..\dist\LicitaSuite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LicitaSuite"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar LicitaSuite"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LicitaSuite"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir LicitaSuite"; Flags: nowait postinstall skipifsilent
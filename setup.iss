[Setup]
AppName=Auto Zapret
AppVersion=1.0.0
AppPublisher=Miukate
DefaultDirName={autopf}\Auto Zapret
DefaultGroupName=Auto Zapret
OutputDir=installer_output
OutputBaseFilename=AutoZapret_Setup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AutoZapret.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Auto Zapret"; Filename: "{app}\AutoZapret.exe"; IconFilename: "{app}\AutoZapret.exe"
Name: "{autodesktop}\Auto Zapret"; Filename: "{app}\AutoZapret.exe"; IconFilename: "{app}\AutoZapret.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AutoZapret.exe"; Description: "{cm:LaunchProgram,Auto Zapret}"; Flags: nowait postinstall skipifsilent
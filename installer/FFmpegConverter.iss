#define MyAppName "FFmpeg Converter"
#define MyAppPublisher "FFmpeg Converter Project"
#define MyAppURL "https://github.com/your-org/ffmpeg-konverter"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{A97350A8-3C72-4F99-8AB2-381A9C4FCD89}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\FFmpeg Converter
DefaultGroupName=FFmpeg Converter
OutputDir=..\dist-installer
OutputBaseFilename=FFmpegConverter-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\FFmpegConverter.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
; Prepare app data folder for first launch/config
Name: "{userappdata}\FFmpeg-Konverter"

[Files]
Source: "..\dist\FFmpegConverter\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\FFmpeg Converter"; Filename: "{app}\FFmpegConverter.exe"
Name: "{autodesktop}\FFmpeg Converter"; Filename: "{app}\FFmpegConverter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FFmpegConverter.exe"; Description: "{cm:LaunchProgram,FFmpeg Converter}"; Flags: nowait postinstall skipifsilent

[Code]
function L(const En, De: string): string;
begin
  if ActiveLanguage = 'german' then
    Result := De
  else
    Result := En;
end;

function HasUninstallSwitch(const Name: string): Boolean;
var
  Tail: string;
  Needle: string;
begin
  Tail := ' ' + Uppercase(GetCmdTail()) + ' ';
  Needle := ' /' + Uppercase(Name) + ' ';
  Result := Pos(Needle, Tail) > 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: string;
  Answer: Integer;
  ForceDelete: Boolean;
  ForceKeep: Boolean;
begin
  if CurUninstallStep <> usPostUninstall then
    Exit;

  AppDataDir := ExpandConstant('{userappdata}\FFmpeg-Konverter');
  if not DirExists(AppDataDir) then
    Exit;

  ForceDelete := HasUninstallSwitch('DELETEUSERDATA');
  ForceKeep := HasUninstallSwitch('KEEPUSERDATA');

  if ForceDelete and ForceKeep then
  begin
    Log('Both DELETEUSERDATA and KEEPUSERDATA set. KEEPUSERDATA wins.');
    ForceDelete := False;
  end;

  if ForceDelete then
  begin
    if DelTree(AppDataDir, True, True, True) then
      Log('Removed user data directory via DELETEUSERDATA: ' + AppDataDir)
    else
      Log('Could not remove user data directory via DELETEUSERDATA: ' + AppDataDir);
    Exit;
  end;

  if ForceKeep then
  begin
    Log('KEEPUSERDATA switch set. Keeping user data at ' + AppDataDir);
    Exit;
  end;

  if UninstallSilent then
  begin
    Log('Silent uninstall: keeping user data at ' + AppDataDir);
    Exit;
  end;

  Answer := SuppressibleMsgBox(
    L(
      'Do you also want to remove user settings and cache in:' + #13#10 + AppDataDir + #13#10 + #13#10 +
      'Choose "No" to keep your config for a later reinstall.',
      'Moechtest du auch Benutzereinstellungen und Cache in folgendem Ordner entfernen:' + #13#10 + AppDataDir + #13#10 + #13#10 +
      'Waehle "Nein", um die Konfiguration fuer eine spaetere Neuinstallation zu behalten.'
    ),
    mbConfirmation,
    MB_YESNO,
    IDNO
  );

  if Answer = IDYES then
  begin
    if DelTree(AppDataDir, True, True, True) then
      Log('Removed user data directory: ' + AppDataDir)
    else
      Log('Could not remove user data directory: ' + AppDataDir);
  end
  else
    Log('User kept data directory: ' + AppDataDir);
end;

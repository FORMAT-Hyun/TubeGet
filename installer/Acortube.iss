; Acortube 설치 마법사 (Inno Setup 6)
; build_installer.bat 이 PyInstaller 빌드 후 자동으로 컴파일합니다.
; 직접 컴파일: ISCC.exe /DMyAppVersion=0.2.0 installer\Acortube.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.2.0"
#endif
#define MyAppName "Acortube"
#define MyAppExe "Acortube.exe"
#define MyAppPublisher "Acortube"

[Setup]
AppId={{6B2E4C1A-9F3D-4E7B-A1C5-3D8F2B7E9A40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} 설치 프로그램
; 설치 폴더: 예전 TubeGet 폴더(예: C:\Program Files\TubeGet)에 설치돼 있었으면 이름을 Acortube 로 바꿔서 쓴다
DefaultDirName={code:GetDefaultDir}
UsePreviousAppDir=no
DisableProgramGroupPage=yes
; 관리자 권한 없이도 설치 가능 (설치 시 '모든 사용자 / 나만' 선택 창이 뜸)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SourceDir=..
OutputDir=dist
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
MinVersion=10.0

[Languages]
#if FileExists(AddBackslash(CompilerPath) + "Languages\Korean.isl")
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면에 바로가기 만들기"; GroupDescription: "바로가기:"
Name: "startup"; Description: "Windows를 켤 때 Acortube 자동 실행"; GroupDescription: "바로가기:"; Flags: unchecked

[Files]
Source: "dist\Acortube\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 시작 메뉴 (모든 앱 목록)
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; AppUserModelID: "Acortube.App"; Comment: "유튜브 다운로더"
; 바탕 화면 (선택)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; AppUserModelID: "Acortube.App"; Tasks: desktopicon
; Windows 시작 시 자동 실행 (선택)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: startup

[InstallDelete]
; 예전 이름(TubeGet)으로 설치된 실행 파일·바로가기 정리 (같은 AppId 라 업데이트로 설치됨)
Type: files; Name: "{app}\TubeGet.exe"
Type: files; Name: "{autoprograms}\TubeGet.lnk"
Type: files; Name: "{autodesktop}\TubeGet.lnk"
Type: files; Name: "{userstartup}\TubeGet.lnk"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Acortube 바로 실행하기"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
const
  UninstKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6B2E4C1A-9F3D-4E7B-A1C5-3D8F2B7E9A40}_is1';

var
  OldDir: String;   // 예전 이름(TubeGet)의 설치 폴더. 없으면 ''

{ 이전에 설치된 위치 (같은 AppId) }
function PreviousAppDir(): String;
begin
  Result := '';
  if IsWin64 then
    RegQueryStringValue(HKA64, UninstKey, 'Inno Setup: App Path', Result);
  if Result = '' then
    RegQueryStringValue(HKA, UninstKey, 'Inno Setup: App Path', Result);
  Result := RemoveBackslashUnlessRoot(Result);
end;

{ 기본 설치 폴더: 처음이면 ...\Acortube, 예전 ...\TubeGet 이면 같은 위치의 ...\Acortube, 그 밖에는 이전 위치 그대로 }
function GetDefaultDir(Param: String): String;
var
  Prev: String;
begin
  Prev := PreviousAppDir();
  OldDir := '';
  if Prev = '' then
    Result := ExpandConstant('{autopf}\{#MyAppName}')
  else if CompareText(ExtractFileName(Prev), 'TubeGet') = 0 then
  begin
    OldDir := Prev;
    Result := AddBackslash(ExtractFileDir(Prev)) + '{#MyAppName}';
  end
  else
    Result := Prev;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  NewDir: String;
begin
  if (OldDir = '') or (not DirExists(OldDir)) then
    exit;
  NewDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  if CompareText(OldDir, NewDir) = 0 then
    exit;   { 사용자가 예전 폴더를 그대로 고른 경우 }
  if CurStep = ssInstall then
  begin
    { 설치 직전: 예전 TubeGet 폴더 이름을 Acortube 로 바꾼다 }
    if not DirExists(NewDir) then
    begin
      if RenameFile(OldDir, NewDir) then
        Log('Renamed ' + OldDir + ' -> ' + NewDir)
      else
        Log('Could not rename ' + OldDir + '; installing into ' + NewDir);
    end;
  end
  else if CurStep = ssPostInstall then
  begin
    { 이름을 바꾸지 못했거나 다른 곳에 설치했으면 남은 예전 폴더를 지운다 (설치 정보는 이미 새 위치를 가리킴) }
    if DirExists(OldDir) then
      DelTree(OldDir, True, True, True);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\Acortube');
    if DirExists(DataDir) and (not UninstallSilent) then
    begin
      if MsgBox('설정, 다운로드 기록, 설치된 도구(yt-dlp, ffmpeg, Deno)도 함께 지울까요?' + #13#10 +
                '(받은 영상·음원 파일은 지워지지 않아요)', mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;

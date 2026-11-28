; Acortube 설치 마법사 (Inno Setup 6)
; build_installer.bat 이 PyInstaller 빌드 후 자동으로 컴파일합니다.
; 직접 컴파일: ISCC.exe /DMyAppVersion=0.2.1 installer\Acortube.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.2.1"
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
; 폴더를 통째로 지우지 않는다 (같은 폴더에 다른 프로그램 파일이 있을 수 있음).
; 우리 앱의 _internal 에 남은 찌꺼기만 지우고, 폴더는 비었을 때만 지운다.
Type: filesandordirs; Name: "{app}\_internal"
Type: dirifempty; Name: "{app}"

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

{ 우리 앱이 설치한 것인지: TubeGet.exe / Acortube.exe, _internal 폴더, 제거 프로그램(unins*) }
function IsOurEntry(Name: String): Boolean;
begin
  Name := Lowercase(Name);
  Result := (Name = 'tubeget.exe') or (Name = 'acortube.exe') or (Name = '_internal') or
            (Copy(Name, 1, 5) = 'unins');
end;

{ 폴더에 우리 파일만 있는지 (같은 이름의 다른 프로그램 'TubeGet' 파일이 섞여 있으면 False) }
function OnlyOurFiles(Dir: String): Boolean;
var
  FindRec: TFindRec;
begin
  Result := True;
  if FindFirst(AddBackslash(Dir) + '*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') and (not IsOurEntry(FindRec.Name)) then
        begin
          Log('Not ours, keeping folder: ' + FindRec.Name);
          Result := False;
          break;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

{ 예전 폴더에서 우리 파일만 지운다. 다른 프로그램 파일은 그대로 두고, 비었을 때만 폴더를 지운다 }
procedure RemoveOurFiles(Dir: String);
var
  FindRec: TFindRec;
  Path: String;
begin
  if FindFirst(AddBackslash(Dir) + '*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') and IsOurEntry(FindRec.Name) then
        begin
          Path := AddBackslash(Dir) + FindRec.Name;
          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
            DelTree(Path, True, True, True)
          else
            DeleteFile(Path);
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
  RemoveDir(Dir);   { 비어 있을 때만 지워진다 }
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
    { 설치 직전: 예전 TubeGet 폴더에 우리 파일만 있을 때만 폴더 이름을 Acortube 로 바꾼다 }
    if (not DirExists(NewDir)) and OnlyOurFiles(OldDir) then
    begin
      if RenameFile(OldDir, NewDir) then
        Log('Renamed ' + OldDir + ' -> ' + NewDir)
      else
        Log('Could not rename ' + OldDir + '; installing into ' + NewDir);
    end;
  end
  else if CurStep = ssPostInstall then
  begin
    { 예전 폴더가 남아 있으면(다른 프로그램 파일이 섞여 있었거나 이름을 못 바꿈) 우리 파일만 정리 }
    if DirExists(OldDir) then
      RemoveOurFiles(OldDir);
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

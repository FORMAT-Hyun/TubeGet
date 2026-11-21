; TubeGet 설치 마법사 (Inno Setup 6)
; build_installer.bat 이 PyInstaller 빌드 후 자동으로 컴파일합니다.
; 직접 컴파일: ISCC.exe /DMyAppVersion=0.1.5 installer\TubeGet.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.1.5"
#endif
#define MyAppName "TubeGet"
#define MyAppExe "TubeGet.exe"
#define MyAppPublisher "TubeGet"

[Setup]
AppId={{6B2E4C1A-9F3D-4E7B-A1C5-3D8F2B7E9A40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} 설치 프로그램
DefaultDirName={autopf}\{#MyAppName}
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
Name: "startup"; Description: "Windows를 켤 때 TubeGet 자동 실행"; GroupDescription: "바로가기:"; Flags: unchecked

[Files]
Source: "dist\TubeGet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 시작 메뉴 (모든 앱 목록)
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; AppUserModelID: "TubeGet.App"; Comment: "유튜브 다운로더"
; 바탕 화면 (선택)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; AppUserModelID: "TubeGet.App"; Tasks: desktopicon
; Windows 시작 시 자동 실행 (선택)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "TubeGet 바로 실행하기"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\TubeGet');
    if DirExists(DataDir) and (not UninstallSilent) then
    begin
      if MsgBox('설정, 다운로드 기록, 설치된 도구(yt-dlp, ffmpeg, Deno)도 함께 지울까요?' + #13#10 +
                '(받은 영상·음원 파일은 지워지지 않아요)', mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;

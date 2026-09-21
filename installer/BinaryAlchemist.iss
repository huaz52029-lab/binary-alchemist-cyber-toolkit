; Inno Setup 6 script for Binary Alchemist Cyber Toolkit v1.0.0.
; Build with: ISCC.exe installer\BinaryAlchemist.iss
; User data lives in %LOCALAPPDATA%\BinaryAlchemist and is kept by default on
; uninstall; the uninstaller asks before deleting it.

#define MyAppName "Binary Alchemist Cyber Toolkit"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Binary Alchemist"
#define MyAppExeName "BinaryAlchemist.exe"

[Setup]
AppId={{5E4B7C21-9F2A-4D8B-B3A6-11C0D64E8F2A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf}\Binary Alchemist
DefaultGroupName=Binary Alchemist
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=BinaryAlchemist-{#MyAppVersion}-Setup
SetupIconFile=..\resources\icons\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription=Network Security Toolkit
VersionInfoCompany={#MyAppPublisher}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\dist\BinaryAlchemist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then begin
    if MsgBox(
      '是否同时删除用户数据？' + #13#10 +
      '这将删除设置、任务历史、报告、CTF 工作区、插件与日志。',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{localappdata}\BinaryAlchemist'), True, True, True);
  end;
end;

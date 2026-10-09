; 遊戲連點器 Windows 安裝程式（Inno Setup 6）
; 不要直接編譯這個檔案：執行 python installer\build.py v1.2.3，它會先用 PyInstaller 打包再呼叫 ISCC。
; 裝的時候不用系統管理員權限，預設裝在 %LOCALAPPDATA%\Programs\遊戲連點器。電腦裡不用裝 Python。

#ifndef AppVersion
  #define AppVersion "dev"
#endif
#define AppName "遊戲連點器"
#define Root ".."

[Setup]
#ifdef TESTBUILD
AppId={{7D1A0B35-TEST-4C6E-8F21-000000000000}
#else
AppId={{B2E94C17-5A3D-4F8B-9C60-1D7E8A3F2B45}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Benjaminwz
AppPublisherURL=https://github.com/Benjaminwz/gameclicker
AppSupportURL=https://github.com/Benjaminwz/gameclicker/issues
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=GameClicker-Setup-Windows-{#AppVersion}
SetupIconFile={#Root}\gameclicker.ico
UninstallDisplayIcon={app}\GameClicker.exe
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "cht"; MessagesFile: "ChineseTraditional.isl"

[Messages]
WelcomeLabel2=這會在你的電腦上安裝 [name/ver]：桌面滑鼠連點器，有按住模式、設定檔、限定遊戲視窗、自訂熱鍵等功能。%n%n不需要另外安裝 Python。
FinishedLabel=裝好了！從開始功能表或桌面的「{#AppName}」打開。%n%n預設熱鍵：F6 開始 / 停止、F7 結束。部分線上遊戲禁止使用自動化工具，使用前請確認遊戲規範。

[Tasks]
Name: "desktopicon"; Description: "在桌面建立「{#AppName}」"; GroupDescription: "捷徑："

[Files]
Source: "build\dist\GameClicker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Root}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Root}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

#ifndef TESTBUILD
[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\GameClicker.exe"; Comment: "桌面滑鼠連點器"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\GameClicker.exe"; Comment: "桌面滑鼠連點器"; Tasks: desktopicon
#endif

[Run]
Filename: "{app}\GameClicker.exe"; Description: "現在打開{#AppName}"; Flags: postinstall nowait skipifsilent

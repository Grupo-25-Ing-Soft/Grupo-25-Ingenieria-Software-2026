; Instalador de Comercial D Nix (Inno Setup 6).
; Va en la raíz del repositorio. Compilar después de ejecutar PyInstaller.

[Setup]
AppId={{6B2F4C1E-25D0-4A7B-9E25-C0DE00D17125}
AppName=Comercial D Nix
AppVersion=4.0.0
AppPublisher=Grupo 25
; Instalación por usuario (sin permisos de administrador). La carpeta queda en
; %LOCALAPPDATA%\Programs y el sistema puede escribir en ella: ahí guarda
; .flask_secret_key y el logotipo que se sube en Configuración.
PrivilegesRequired=lowest
DefaultDirName={autopf}\ComercialDNix
DefaultGroupName=Comercial D Nix
DisableProgramGroupPage=yes
OutputDir=instalador
OutputBaseFilename=Instalador_ComercialDNix_4.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\ComercialDNix\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Comercial D Nix"; Filename: "{app}\ComercialDNix.exe"
Name: "{autodesktop}\Comercial D Nix"; Filename: "{app}\ComercialDNix.exe"

[Run]
Filename: "{app}\ComercialDNix.exe"; Description: "Abrir Comercial D Nix"; Flags: nowait postinstall skipifsilent

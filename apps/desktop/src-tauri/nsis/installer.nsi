; BUG-FRONTEND-RT-11 (event 000040): the previous installer
; would fail mid-install with a NSIS error like "Cannot open
; file: flowntier_runtime.exe" if a previous Flowntier
; instance was still running. This .onInit hook uses Win32
; Toolhelp32 (built into Windows since XP) to detect the
; running `flowntier.exe` process and prompts the user to
; close it before the installer continues.

; Find a process by name. Sets $0 to the process PID, or empty
; string if not found. Uses the PSAPI dll (built into Windows
; since XP) — no extra plugin dependency.
Function FindProcess
    Exch $R0  ; process name
    Push $R1  ; PID
    Push $R2  ; snapshot handle
    Push $R3  ; process entry
    Push $R4  ; current process first

    ; Default: not found
    StrCpy $0 ""

    System::Alloc 4
    Pop $R4
    System::Call "kernel32::GetCurrentProcessId i.R4"

    ; Take process snapshot
    System::Call "kernel32::CreateToolhelp32Snapshot iii" (0x2, 0) i.r2
    ${If} $R2 != 0
        System::Alloc ${NSIS_MAX_STRLEN}
        Pop $R3
        System::Call "kernel32::Process32First i.r2 i.r3"

        ${Do}
            System::Call "kernel32::lstrcmpiA t(r3+44) t(R0)i.r1"
            ${If} $R1 == 0
                ; Match — copy PID
                System::Call "*$R4 i.r1"
                StrCpy $0 $R1
                ${Break}
            ${EndIf}
            System::Call "kernel32::Process32Next i.r2 i.r3"
        ${LoopUntil} $R1 == 0

        System::Free $R3
        System::Call "kernel32::CloseHandle i.r2"
    ${EndIf}

    Pop $R4
    Pop $R3
    Pop $R2
    Pop $R1
    Exch $0
FunctionEnd

; Custom .onInit handler. We use a unique function name
; (customOnInit) to avoid colliding with Tauri's own .onInit.
; Tauri's NSIS template exposes `customOnInit` for users to
; define their own pre-install logic — see
; https://v2.tauri.org/distribute/windows-installer/
Function customOnInit
    ; Check if Flowntier is running BEFORE the installer UI
    ; shows. This gives the user a chance to close the app before
    ; the installer starts touching files.
    Push "flowntier.exe"
    Call FindProcess
    Pop $0
    ${If} $0 != ""
        MessageBox MB_YESNO|MB_ICONEXCLAMATION|MB_TOPMOST \
            "Flowntier is currently running.$\r$\n$\r$\n\
             Please close Flowntier before continuing this install.$\r$\n$\r$\n\
             Click [Yes] after closing Flowntier.$\r$\n\
             Click [No] to cancel the install." \
            IDYES +2 IDNO abort_install
        Abort
        abort_install:
        Abort
    ${EndIf}
FunctionEnd
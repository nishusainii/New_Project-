<#
==============================================================================
Script: optimize-and-seal-windows-vdi.ps1
Purpose: Enterprise-Grade VDI Optimization, Bloatware Removal, Log Truncation,
         and Sysprep Generalization for Windows 10/11 on Proxmox VE.
Target OS: Windows 10 (21H2/22H2) & Windows 11 (22H2/23H2/24H2) x64
Execution: Run within the Build VM from an elevated Administrator PowerShell prompt.
Usage: powershell.exe -ExecutionPolicy Bypass -File .\optimize-and-seal-windows-vdi.ps1
==============================================================================
#>

#Requires -RunAsAdministrator
[CmdletBinding()]
Param(
    [switch]$SkipSysprep = $false,
    [string]$UnattendPath = "$PSScriptRoot\unattend.xml",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"
$LogPath = "C:\Windows\Temp\vdi-optimization-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Formatted = "[$Timestamp] [$Level] $Message"
    switch ($Level) {
        "INFO"    { Write-Host $Formatted -ForegroundColor Cyan }
        "SUCCESS" { Write-Host $Formatted -ForegroundColor Green }
        "WARN"    { Write-Host $Formatted -ForegroundColor Yellow }
        "ERROR"   { Write-Host $Formatted -ForegroundColor Red }
    }
    $Formatted | Out-File -FilePath $LogPath -Append -Encoding utf8
}

Clear-Host
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "       WINDOWS VDI GOLDEN IMAGE OPTIMIZATION & SEALING SUITE          " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Target Hypervisor: Proxmox Virtual Environment (PVE)                 "
Write-Host " Target Architecture: q35 / OVMF UEFI / VirtIO SCSI / vTPM 2.0        "
Write-Host " Log File: $LogPath                                                  "
Write-Host "======================================================================"

# ------------------------------------------------------------------------------
# Phase 0: Pre-Flight Safety Checks
# ------------------------------------------------------------------------------
Write-Log "Verifying administrative privileges and operating system..."

$OS = Get-CimInstance Win32_OperatingSystem
Write-Log "Detected Operating System: $($OS.Caption) (Version: $($OS.Version), Build: $($OS.BuildNumber))"

# Check VirtIO Drivers
$VirtioScsi = Get-PnpDevice -Class "SCSIAdapter" -Status "OK" -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -like "*VirtIO*" -or $_.Manufacturer -like "*Red Hat*" }
if ($VirtioScsi) {
    Write-Log "VirtIO SCSI Storage Controller detected: $($VirtioScsi.FriendlyName)" "SUCCESS"
} else {
    Write-Log "VirtIO SCSI Driver NOT detected. Ensure VirtIO drivers are installed!" "WARN"
}

$VirtioNet = Get-PnpDevice -Class "Net" -Status "OK" -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -like "*VirtIO*" -or $_.Manufacturer -like "*Red Hat*" }
if ($VirtioNet) {
    Write-Log "VirtIO Network Adapter detected: $($VirtioNet.FriendlyName)" "SUCCESS"
} else {
    Write-Log "VirtIO Network Driver NOT detected. Ensure VirtIO drivers are installed!" "WARN"
}

# Check QEMU Guest Agent Service
$QemuGaService = Get-Service -Name "qemu-ga" -ErrorAction SilentlyContinue
if ($QemuGaService) {
    Write-Log "QEMU Guest Agent service found (Status: $($QemuGaService.Status)). Setting startup to Automatic." "SUCCESS"
    Set-Service -Name "qemu-ga" -StartupType Automatic
    if ($QemuGaService.Status -ne "Running") {
        Start-Service -Name "qemu-ga" -ErrorAction SilentlyContinue
    }
} else {
    Write-Log "CRITICAL: QEMU Guest Agent (qemu-ga) service is NOT installed!" "ERROR"
    Write-Log "Please install 'virtio-win-guest-tools.exe' from the VirtIO CD-ROM before sealing." "ERROR"
    if (-not $Force) {
        $Continue = Read-Host "Proceed without QEMU Guest Agent? (Not recommended) [y/N]"
        if ($Continue -ne 'y' -and $Continue -ne 'Y') {
            Write-Log "Optimization halted by operator." "WARN"
            Exit 1
        }
    }
}

# Check Balloon Service
$BalloonService = Get-Service -Name "BalloonService" -ErrorAction SilentlyContinue
if ($BalloonService) {
    Write-Log "VirtIO Balloon Service found. Setting startup to Automatic." "SUCCESS"
    Set-Service -Name "BalloonService" -StartupType Automatic
}

if (-not $Force) {
    $Confirm = Read-Host "`nProceed with VDI optimization and Sysprep preparation? [y/N]"
    if ($Confirm -ne 'y' -and $Confirm -ne 'Y') {
        Write-Log "Aborted by operator." "WARN"
        Exit 0
    }
}

# ------------------------------------------------------------------------------
# Phase 1: Remote Desktop Protocol (RDP) & Network Configuration
# ------------------------------------------------------------------------------
Write-Log "--- Phase 1: Configuring Remote Desktop Protocol (RDP) ---"

# Enable Remote Desktop
$TsPath = "HKLM:\System\CurrentControlSet\Control\Terminal Server"
Set-ItemProperty -Path $TsPath -Name "fDenyTSConnections" -Value 0 -Type DWord
Write-Log "Remote Desktop enabled (fDenyTSConnections = 0)."

# Enable Network Level Authentication (NLA) for security
$RdpTcpPath = "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp"
Set-ItemProperty -Path $RdpTcpPath -Name "UserAuthentication" -Value 1 -Type DWord
Write-Log "Network Level Authentication (NLA) enforced."

# Enable Audio Redirection over RDP (Capture and Playback)
Set-ItemProperty -Path $RdpTcpPath -Name "fDisableAudioCapture" -Value 0 -Type DWord
Set-ItemProperty -Path $RdpTcpPath -Name "fDisableCam" -Value 0 -Type DWord
Write-Log "RDP Audio & Webcam redirection enabled."

# Enable Windows Defender Firewall rules for RDP
Enable-NetFirewallRule -DisplayGroup "Remote Desktop" -ErrorAction SilentlyContinue
Write-Log "Firewall rule group 'Remote Desktop' enabled."

# ------------------------------------------------------------------------------
# Phase 2: Power, Disk, & VDI Performance Tuning
# ------------------------------------------------------------------------------
Write-Log "--- Phase 2: Power, Disk & Storage Performance Tuning ---"

# Disable Hibernation (Eliminates multi-gigabyte hiberfil.sys & disables Fast Startup)
Write-Log "Disabling hibernation and Fast Startup to recover disk space..."
& powercfg.exe /hibernate off
Write-Log "Hibernation disabled (hiberfil.sys removed)." "SUCCESS"

# Set Power Plan to High Performance
Write-Log "Activating High Performance Power Plan..."
$HighPerfGuid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
& powercfg.exe -setactive $HighPerfGuid
Write-Log "Power plan set to High Performance."

# Disable Superfetch / SysMain (Prevent IOPS storms on hypervisor storage pools)
Write-Log "Disabling SysMain (Superfetch) service..."
Stop-Service -Name "SysMain" -Force -ErrorAction SilentlyContinue
Set-Service -Name "SysMain" -StartupType Disabled -ErrorAction SilentlyContinue

# Disable Windows Search Indexing (WSearch) to stop disk write amplification
Write-Log "Disabling Windows Search Indexer service (prevents SAN/ZFS write bottlenecks)..."
Stop-Service -Name "WSearch" -Force -ErrorAction SilentlyContinue
Set-Service -Name "WSearch" -StartupType Disabled -ErrorAction SilentlyContinue

# Disable Scheduled Defragmentation (Virtual disks are managed by Hypervisor TRIM/Discard)
Write-Log "Disabling guest scheduled defragmentation..."
Disable-ScheduledTask -TaskPath "\Microsoft\Windows\Defrag\" -TaskName "ScheduledDefrag" -ErrorAction SilentlyContinue

# Disable Windows Consumer Cloud Experience (Auto-install of recommended Store apps)
$CloudContent = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent"
if (-not (Test-Path $CloudContent)) { New-Item -Path $CloudContent -Force | Out-Null }
Set-ItemProperty -Path $CloudContent -Name "DisableWindowsConsumerFeatures" -Value 1 -Type DWord
Write-Log "Consumer Cloud app auto-installation disabled."

# Optimize Visual Effects (Adjust for performance, keep Smooth Font Edges for readability)
Write-Log "Optimizing visual effects for low-latency VDI streaming..."
$DesktopReg = "HKCU:\Control Panel\Desktop"
Set-ItemProperty -Path $DesktopReg -Name "FontSmoothing" -Value "2"
Set-ItemProperty -Path $DesktopReg -Name "FontSmoothingType" -Value 2 -Type DWord
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Value 3 -Type DWord -ErrorAction SilentlyContinue

# ------------------------------------------------------------------------------
# Phase 3: Telemetry, Diagnostics, & Background Services
# ------------------------------------------------------------------------------
Write-Log "--- Phase 3: Disabling Telemetry, Diagnostics & Xbox Services ---"

# Services to stop and disable
$ServicesToDisable = @(
    "DiagTrack",              # Connected User Experiences and Telemetry
    "dmwappushservice",       # Device Management Wireless Application Protocol (WAP) Push
    "XblAuthManager",         # Xbox Live Auth Manager
    "XblGameSave",            # Xbox Live Game Save Service
    "XboxNetApiSvc",          # Xbox Live Networking Service
    "XboxGipSvc",             # Xbox Accessory Management Service
    "WerSvc",                 # Windows Error Reporting Service
    "RetailDemo"              # Retail Demo Service
)

foreach ($Svc in $ServicesToDisable) {
    if (Get-Service -Name $Svc -ErrorAction SilentlyContinue) {
        Stop-Service -Name $Svc -Force -ErrorAction SilentlyContinue
        Set-Service -Name $Svc -StartupType Disabled -ErrorAction SilentlyContinue
        Write-Log "Service '$Svc' stopped and disabled."
    }
}

# Registry Policies: Disable Telemetry & Cortana
$DataCollection = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
if (-not (Test-Path $DataCollection)) { New-Item -Path $DataCollection -Force | Out-Null }
Set-ItemProperty -Path $DataCollection -Name "AllowTelemetry" -Value 0 -Type DWord

$WinSearch = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search"
if (-not (Test-Path $WinSearch)) { New-Item -Path $WinSearch -Force | Out-Null }
Set-ItemProperty -Path $WinSearch -Name "AllowCortana" -Value 0 -Type DWord
Set-ItemProperty -Path $WinSearch -Name "DisableWebSearch" -Value 1 -Type DWord
Set-ItemProperty -Path $WinSearch -Name "ConnectedSearchUseWeb" -Value 0 -Type DWord
Write-Log "Telemetry and Cortana policies disabled."

# ------------------------------------------------------------------------------
# Phase 4: AppX Modern Package Cleaning (Prevents Sysprep 0x80073cf2)
# ------------------------------------------------------------------------------
Write-Log "--- Phase 4: Cleaning Provisioned AppX Packages (Sysprep Safeguard) ---"

# Stop Windows Update and Store Install services to prevent downloads during sealing
Stop-Service -Name "wuauserv" -Force -ErrorAction SilentlyContinue
Stop-Service -Name "AppXSvc" -Force -ErrorAction SilentlyContinue
Stop-Service -Name "InstallService" -Force -ErrorAction SilentlyContinue

$BloatwarePatterns = @(
    "*Microsoft.BingNews*",
    "*Microsoft.BingWeather*",
    "*Microsoft.GamingApp*",
    "*Microsoft.GetHelp*",
    "*Microsoft.Getstarted*",
    "*Microsoft.MicrosoftOfficeHub*",
    "*Microsoft.MicrosoftSolitaireCollection*",
    "*Microsoft.People*",
    "*Microsoft.SkypeApp*",
    "*Microsoft.Todos*",
    "*Microsoft.WindowsFeedbackHub*",
    "*Microsoft.Xbox*",
    "*Microsoft.ZuneMusic*",
    "*Microsoft.ZuneVideo*",
    "*Clipchamp.Clipchamp*",
    "*SpotifyAB.SpotifyMusic*"
)

foreach ($Pattern in $BloatwarePatterns) {
    # Remove Provisioned Packages (Machine-wide)
    Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -like $Pattern } | ForEach-Object {
        Write-Log "Removing Provisioned AppX: $($_.DisplayName)"
        Remove-AppxProvisionedPackage -Online -PackageName $_.PackageName -ErrorAction SilentlyContinue | Out-Null
    }
    # Remove Current User AppX
    Get-AppxPackage -Name $Pattern -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Log "Removing User AppX: $($_.Name)"
        Remove-AppxPackage -Package $_.PackageFullName -ErrorAction SilentlyContinue | Out-Null
    }
}

# ------------------------------------------------------------------------------
# Phase 5: Storage Reclamation & Log Truncation
# ------------------------------------------------------------------------------
Write-Log "--- Phase 5: Deep Storage Reclamation & Log Truncation ---"

# 1. Clean Windows Update Download Cache
$WUDir = "C:\Windows\SoftwareDistribution\Download"
if (Test-Path $WUDir) {
    Write-Log "Purging Windows Update cache in $WUDir..."
    Get-ChildItem -Path $WUDir -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# 2. Clean Temporary Folders
$TempDirs = @("C:\Windows\Temp", "$env:TEMP")
foreach ($Dir in $TempDirs) {
    if (Test-Path $Dir) {
        Write-Log "Cleaning temporary directory: $Dir"
        Get-ChildItem -Path $Dir -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -ne $LogPath } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 3. Clean Crash Dumps and Memory Dumps
$DumpDirs = @("C:\Windows\Minidump", "C:\Windows\MEMORY.DMP")
foreach ($Dump in $DumpDirs) {
    if (Test-Path $Dump) {
        Write-Log "Removing crash dump: $Dump"
        Remove-Item -Path $Dump -Force -Recurse -ErrorAction SilentlyContinue
    }
}

# 4. Clear Windows Event Logs
Write-Log "Truncating all Windows Event Logs..."
Get-WinEvent -ListLog * -ErrorAction SilentlyContinue | Where-Object { $_.RecordCount -gt 0 -and $_.IsEnabled } | ForEach-Object {
    try {
        [System.Diagnostics.Eventing.Reader.EventLogSession]::GlobalSession.ClearLog($_.LogName)
    } catch {
        # Some event logs are locked by system kernel, ignore gracefully
    }
}
Write-Log "Event logs cleared."

# 5. Execute DISM Component Cleanup
Write-Log "Executing DISM Component Store cleanup (/StartComponentCleanup /ResetBase)..."
Write-Log "This may take 3-5 minutes. Please wait..."
& Dism.exe /Online /Cleanup-Image /StartComponentCleanup /ResetBase
Write-Log "DISM component cleanup complete." "SUCCESS"

# ------------------------------------------------------------------------------
# Phase 6: Sysprep Staging & Sealing Execution
# ------------------------------------------------------------------------------
Write-Log "--- Phase 6: Sysprep Staging and Execution ---"

$SysprepDir = "C:\Windows\System32\Sysprep"
$StagedUnattend = "$SysprepDir\unattend.xml"

if (Test-Path $UnattendPath) {
    Write-Log "Copying answer file from '$UnattendPath' to '$StagedUnattend'..."
    Copy-Item -Path $UnattendPath -Destination $StagedUnattend -Force
    Write-Log "Sysprep answer file staged successfully." "SUCCESS"
} else {
    Write-Log "WARNING: Unattend file '$UnattendPath' not found!" "WARN"
    if (Test-Path $StagedUnattend) {
        Write-Log "Using existing staged answer file at '$StagedUnattend'." "INFO"
    } else {
        Write-Log "No unattend.xml found in $SysprepDir. Sysprep will run without answer file." "WARN"
    }
}

# Verify Sysprep Registry Keys
$SysprepReg = "HKLM:\SYSTEM\Setup\Status\SysprepStatus"
if (Test-Path $SysprepReg) {
    Set-ItemProperty -Path $SysprepReg -Name "GeneralizationState" -Value 7 -Type DWord -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $SysprepReg -Name "CleanUpState" -Value 2 -Type DWord -ErrorAction SilentlyContinue
}

Write-Log "Golden Image Optimization and Preparation successfully completed!" "SUCCESS"
Write-Log "======================================================================"
Write-Log " READY FOR SYSPREP SEALING"
Write-Log " Command: sysprep.exe /generalize /oobe /shutdown /unattend:unattend.xml"
Write-Log "======================================================================"

if ($SkipSysprep) {
    Write-Log "[-SkipSysprep flag supplied. Sysprep was NOT launched. System remains active.]" "WARN"
    Exit 0
}

Write-Host "`nWARNING: The virtual machine will now be generalized and powered off." -ForegroundColor Red
Write-Host "Do NOT power the VM back on until it has been converted to a Proxmox Template!" -ForegroundColor Yellow

$SealNow = "y"
if (-not $Force) {
    $SealNow = Read-Host "`nExecute Sysprep and power off now? [Y/n]"
}

if ($SealNow -eq 'n' -or $SealNow -eq 'N') {
    Write-Log "Sysprep execution postponed by user." "WARN"
    Write-Log "To seal manually later, run:" "INFO"
    Write-Log "C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /shutdown /unattend:C:\Windows\System32\Sysprep\unattend.xml" "INFO"
    Exit 0
}

Write-Log "Executing Sysprep Generalization with answer file..."
Set-Location -Path $SysprepDir
& "$SysprepDir\sysprep.exe" /generalize /oobe /shutdown "/unattend:$StagedUnattend"

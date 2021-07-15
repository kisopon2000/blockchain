#===============================================================================
# Setup-Container.ps1
#===============================================================================
param(
	[String]$ArchiveFile,    # システムアーカイブ
	[String]$Product,        # プロダクト名
	[Switch]$Help            # 使用方法表示
)

#--------------------------------------
# 変数設定
#--------------------------------------
Set-Variable CUR_DIR               "$(Split-Path $myInvocation.MyCommand.Path -parent)"           -option constant
Set-Variable LOG_FILE              "$($script:CUR_DIR)\setup.log"                                 -option constant
Set-Variable OUT_DIR               "C:/opt/$($script:Product)"                                    -option constant
Set-Variable SYS_DIR               "$($script:OUT_DIR)"                                           -option constant
Set-Variable WIN_DIR               "$($script:CUR_DIR)\win"                                       -option constant

Set-Variable SQLSVR_SETUP_PATH     "$($script:WIN_DIR)\database_en\SETUP.EXE"                     -option constant
Set-Variable SQLSVR_INSTANCE       "PWSP"                                                         -option constant
Set-Variable SQLSVR_PASS           "Rencho2000"                                                   -option constant
Set-Variable SQLSVR_USR_TOOL_PATH  "$($script:CUR_DIR)\db_create_user.bat"                        -option constant
Set-Variable SQLSVR_MOUNT_DIR      "C:\sqlserver\data"                                            -option constant

Set-Variable VIM_TOOL_PATH         "$($script:WIN_DIR)\gvim82.exe"                                -option constant
Set-Variable PS_PROFILE_DIR        "C:\Users\ContainerAdministrator\Documents\WindowsPowerShell"  -option constant
Set-Variable PS_PROFILE_PATH       "$($script:WIN_DIR)\Microsoft.PowerShell_profile.ps1"          -option constant

#--------------------------------------
# 使用方法
#--------------------------------------
function Print-Usage(
	[String]$Message
)
{
Write-Host "==========================================================="
Write-Host " $($myInvocation.ScriptName)"
Write-Host "---------------------------usage---------------------------"
Write-Host " usage: $($myInvocation.ScriptName)"
Write-Host " option:"
Write-Host "     -ArchiveFile   : archive module path"
Write-Host "     -Product       : product name"
Write-Host "     -Help:         : show usage"
Write-Host "==========================================================="
if ($Message) { Write-Host "$($Message)" }
}

#--------------------------------------
# ログ出力
#--------------------------------------
function Print-Log(
	[String]$Message)
{
    Write-Host $Message
    $Message = (Get-Date -format s) + ": " + $Message
    Write-Output $Message| Out-File $script:LOG_FILE -encoding default -Append
}

#--------------------------------------
# ツール削除
#--------------------------------------
function Clear-SetupTool()
{
    if (![string]::IsNullOrEmpty($script:ArchiveFile)) {
        if ($(Test-Path "$($script:CUR_DIR)\$($script:ArchiveFile)")){ Remove-Item "$($script:CUR_DIR)\$($script:ArchiveFile)" -Force }
    }
    if ($(Test-Path "$($script:WIN_DIR)"))                       { Remove-Item "$($script:WIN_DIR)"                        -Force -Recurse }
	if ($(Test-Path "$($myInvocation.ScriptName)"))              { Remove-Item "$($myInvocation.ScriptName)"               -Force }
}

#--------------------------------------
# 展開先作成
#--------------------------------------
function Create-Path()
{
	Print-Log "***** [Create-Path] start!! *****"
	
	# インテグレーションディレクトリ作成
	New-Item -ItemType Directory "$($script:OUT_DIR)" | Out-Null
	if ($(Test-Path "$($script:OUT_DIR)") -eq $FALSE) {
		Print-Log "<!> mkdir($($script:OUT_DIR)) failed..."
		return 1
	}
	Print-Log "<I> mkdir($($script:OUT_DIR))"

    # ホストとの共有ディレクトリ作成
	New-Item -ItemType Directory "$($script:SQLSVR_MOUNT_DIR)" | Out-Null
	if ($(Test-Path "$($script:SQLSVR_MOUNT_DIR)") -eq $FALSE) {
		Print-Log "<!> mkdir($($script:SQLSVR_MOUNT_DIR)) failed..."
		return 1
	}
	Print-Log "<I> mkdir($($script:SQLSVR_MOUNT_DIR))"

	Print-Log "***** [Create-Path] done!! *****"

    return 0
}

#--------------------------------------
# zip展開
#--------------------------------------
function Extract-Archive([String]$File)
{
	Print-Log "***** [Extract-Archive] start!! *****"

	if ($(Test-Path $File) -eq $FALSE) {
		Print-Log "<!> $($File) not found."
		return 1
	}

	# 展開
    Expand-Archive -Path "$($File)" -DestinationPath "$($script:OUT_DIR)" | Out-Null
	if ($? -eq $false) {
		Print-Log "<!> unzip.exe failed..."
		return 1
	}
	Print-Log "<I> extract archive $($File) to $($OUT_DIR)"

	Print-Log "***** [Extract-Archive] done!! *****"

    return 0
}

#--------------------------------------
# DBインスタンス追加
#--------------------------------------
function Add-DBInstance()
{
	Print-Log "***** [Add-DBInstance] start!! *****"

	if ($(Test-Path $script:SQLSVR_SETUP_PATH) -eq $FALSE) {
		Print-Log "<!> $($script:SQLSVR_SETUP_PATH) not found."
		return 1
	}

	# DBインスタンス追加
    & $script:SQLSVR_SETUP_PATH /Q /ACTION=Install /IACCEPTSQLSERVERLICENSETERMS /FEATURES=SQLEngine,Conn /INSTANCENAME=$script:SQLSVR_INSTANCE /SECURITYMODE=SQL /SAPWD=$script:SQLSVR_PASS /NPENABLED=1 /TCPENABLED=1 /AGTSVCACCOUNT='NT AUTHORITY\NETWORK SERVICE' /SQLSVCACCOUNT='NT AUTHORITY\NETWORK SERVICE' /SQLSYSADMINACCOUNTS='BUILTIN\ADMINISTRATORS' | Out-Null
	if ($? -eq $false) {
		Print-Log "<!> add db instance failed..."
		return 1
	}
	Print-Log "<I> add db instance $($script:DBInstance)"

	Print-Log "***** [Add-DBInstance] done!! *****"

    return 0
}

#--------------------------------------
# DBユーザー追加
#--------------------------------------
function Add-DBUser()
{
	Print-Log "***** [Add-DBUser] start!! *****"

    if ($(Test-Path $script:SQLSVR_USR_TOOL_PATH) -eq $FALSE) {
		Print-Log "<!> $($script:SQLSVR_USR_TOOL_PATH) not found."
		return 1
	}

	# DBユーザー追加
    & $script:SQLSVR_USR_TOOL_PATH
	if ($? -eq $false) {
		Print-Log "<!> add db user failed..."
		return 1
	}

	Print-Log "***** [Add-DBUser] done!! *****"

    return 0
}

#--------------------------------------
# databaseセットアップ
#--------------------------------------
function Setup-Database()
{
	Print-Log "***** [Setup-Database] start!! *****"

    # DBインスタンス追加
	$ret = Add-DBInstance
	if ($ret -ne 0) {
		Print-Log "<!> Add-DBInstance failed..."
		return $ret
	}

    # DBユーザー追加
    $ret = Add-DBUser
	if ($ret -ne 0) {
		Print-Log "<!> Add-DBUser failed..."
		return $ret
	}

	Print-Log "***** [Setup-Database] done!! *****"

    return 0
}

#--------------------------------------
# utilityセットアップ
#--------------------------------------
function Setup-Utility()
{
	Print-Log "***** [Setup-Utility] start!! *****"

    if ($(Test-Path $script:VIM_TOOL_PATH) -eq $FALSE) {
		Print-Log "<!> $($script:VIM_TOOL_PATH) not found."
		return 1
	}

    # VIM追加
    & $script:VIM_TOOL_PATH /S
    if ($? -eq $false) {
		Print-Log "<!> add vim failed..."
		return 1
	}
    $waitcount = 10
    $waitcounter = 0
    While ($true) {
        $process = Get-Process | Where-Object { $_.ProcessName -like "*vim*" }
        if ($process -eq $null) {
            break
        } else {
            Start-Sleep 5
            $waitcounter++
            if ($waitcounter -ge $waitcount) {
                Print-Log "<!> add vim timeout failed..."
		        return 1
            }
        }
    }
	Print-Log "<I> add vim"

    if ($(Test-Path $script:PS_PROFILE_PATH) -eq $FALSE) {
		Print-Log "<!> $($script:PS_PROFILE_PATH) not found."
		return 1
	}
    if ($(Test-Path $script:PS_PROFILE_DIR) -eq $FALSE) {
        New-Item $script:PS_PROFILE_DIR -ItemType Directory | Out-Null
    }

    # Powershellプロファイル追加
    Copy-Item -Path $script:PS_PROFILE_PATH -Destination "$($script:PS_PROFILE_DIR)\Microsoft.PowerShell_profile.ps1" | Out-Null
    if ($? -eq $false) {
		Print-Log "<!> add powershell profile failed..."
		return 1
	}
	Print-Log "<I> add powershell profile"

	Print-Log "***** [Setup-Utility] done!! *****"

    return 0
}

#--------------------------------------
# ベースセットアップ
#--------------------------------------
function Setup-Base()
{
    # database
    $ret = Setup-Database
	if ($ret -ne 0) {
		Print-Log "<!> Setup-Database failed..."
		return 1
	}

    # utility
    $ret = Setup-Utility
	if ($ret -ne 0) {
		Print-Log "<!> Setup-Utility failed..."
		return 1
	}

    return 0
}

#--------------------------------------
# プロダクトセットアップ
#--------------------------------------
function Setup-Prod()
{
	# プロダクト固有の処理

    return 0
}

#--------------------------------------
# イニシャライズ
#--------------------------------------
function Initialize()
{
    # 展開先作成
	$ret = Create-Path
	if ($ret -ne 0) {
		Print-Log "<!> Create-Path failed..."
		return $ret
	}

	# システムアーカイブ展開
	if ([string]::IsNullOrEmpty($script:ArchiveFile)) {
		Print-Log "<I> non system install..."
	} else {
		if ($(Test-Path "$($script:CUR_DIR)\$($script:ArchiveFile)")) {
			$ret = Extract-Archive "$($script:CUR_DIR)\$($script:ArchiveFile)"
			if ($ret -ne 0) {
				Print-Log "<!> Extract-Archive(system) failed..."
				return $ret
			}
		} else {
			Print-Log "<I> skip system install..."
		}
	}

    return 0
}

#--------------------------------------
# メイン
#--------------------------------------
function Main()
{
	Print-Log "_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/"
	Print-Log " setup container..."
	Print-Log "_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/"

	$ret = Setup-Base
	if ($ret -ne 0) {
		Print-Log "xxxxxxxxxxxxxxxxxxxxxxxx"
		Print-Log "<!> Setup-Base failed..."
		Print-Log "xxxxxxxxxxxxxxxxxxxxxxxx"
		return $ret
	}

	if ($script:Product -ne "") {
		Print-Log "$($script:Product) configure..."
		$ret = Setup-Prod
		if ($ret -ne 0) {
			Print-Log "xxxxxxxxxxxxxxxxxxxxxxxx"
			Print-Log "<!> Setup-Prod failed..."
			Print-Log "xxxxxxxxxxxxxxxxxxxxxxxx"
			return $ret
		}
	}

	Print-Log "_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/"
	Print-Log " finished!!"
	Print-Log "_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/"

    return 0
}

#--------------------------------------
# ファイナライズ
#--------------------------------------
function Finalize()
{
    # ゴミ掃除
	$ret = Clear-SetupTool

    return 0
}

#--------------------------------------
# エントリーポイント
#--------------------------------------
$ret = Initialize
if ($ret -eq 0) {
    $ret = Main
    Finalize
}
exit $ret

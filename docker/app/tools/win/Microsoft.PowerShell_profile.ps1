"RTC Container PowerShell"

#--------------------------------------
# 定数
#--------------------------------------
Set-Variable DB_SQLSVR_DRIVER "{ODBC Driver 13 for SQL Server}" -option constant
Set-Variable DB_SQLSVR_USER   "Dashboard_Admin"                 -option constant
Set-Variable DB_SQLSVR_PASS   "P@ssW0rd"                        -option constant
Set-Variable DB_MYSQL_DRIVER  "{MySQL ODBC 8.0 ANSI Driver}"    -option constant
Set-Variable DB_MYSQL_USER    "root"                            -option constant
Set-Variable DB_MYSQL_PASS    "Rencho2000"                      -option constant

#--------------------------------------
# エイリアス
#--------------------------------------
set-alias vi 'C:\Program Files (x86)\Vim\vim82\vim.exe'

#--------------------------------------
# DBコンフィグ設定
#--------------------------------------
function Setup-DBConfig([string]$DBType, [string]$DBServer, [string]$DBName)
{
    if ([string]::IsNullOrEmpty($DBType)) {
        Write-Host "<!> DBType is empty" -ForegroundColor Red
        return 1
    }

    if ([string]::IsNullOrEmpty($DBServer)) {
        Write-Host "<!> DBServer is empty" -ForegroundColor Red
        return 1
    }

    if ([string]::IsNullOrEmpty($DBName)) {
        Write-Host "<!> DBName is empty" -ForegroundColor Red
        return 1
    }

    # プロダクト名取得
    $prod = (ls "C:\opt").Name
    if ([string]::IsNullOrEmpty($prod)) {
        Write-Host "<!> product not found" -ForegroundColor Red
        return 1
    }
    
    # DBコンフィグファイルパス取得
    $config = "C:\opt\$($prod)\web\cgi-bin\config\config.xml"
    if ($(Test-Path $config) -eq $FALSE) {
		Write-Host "<!> $($config) not found." -ForegroundColor Red
		return 1
	}

    # DBコンフィグ設定
    $xml = [xml](Get-Content $config)
    $xml.config.db.server = $DBServer
    $xml.config.db.dbname = $DBName
    if ($DBType -eq 'sqlserver') {
        $xml.config.db.driver = $script:DB_SQLSVR_DRIVER
        $xml.config.db.uid = $script:DB_SQLSVR_USER
        $xml.config.db.pwd = $script:DB_SQLSVR_PASS
    } elseif($DBType -eq 'mysql') {
        $xml.config.db.driver = $script:DB_MYSQL_DRIVER
        $xml.config.db.uid = $script:DB_MYSQL_USER
        $xml.config.db.pwd = $script:DB_MYSQL_PASS
    } else {
        Write-Host "<!> Not support $DBType" -ForegroundColor Red
        return 1
    }
    $xml.Save($config)

    return 0
}

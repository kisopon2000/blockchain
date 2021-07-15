@echo off
break on
set CWD=%~dp0
set SysRootPath=%CWD%..\..\..\
REM =============================================
REM データベースの復元
REM 起動パラメータ
REM 1:サーバー名 2:復元ファイルパス 3:ログファイルフォルダ 4:ユーザーID 5:パスワード 6:mdf/ldfのファイルフォルダ 7:データベース名
REM --------------------------------
REM 動作
REM 1.Dashboard_Adminユーザーでログイン
REM 2.「データベース名」のデータベース作成(復元)
REM 3.ユーザー再作成 ･･･ 「Dashboard_Admin」が存在すれば、一度ユーザーを削除
REM 4.ユーザーマッピングを実行 (dbo) 
REM 5.「Dashboard_Admin」で接続確認
REM =============================================

REM DBサーバー名
Set ServerName=localhost\PWSP

REM DBユーザー
Set Database=exchange
Set UserID=Rtc_Admin
Set Password=P@ssW0rd

REM 入力ファイルパス
Set inFilePath=%CWD%..\..\db\exchange.bak

REM ログ出力先
Set LogPath=%CWD%

REM mdf/ldfのファイル
Set sqlserverDataPath=C:\HOME\rtc\db
if not exist %sqlserverDataPath% (
    mkdir %sqlserverDataPath%
)

REM 起動パラメータチェック
if "%1"=="" (set ServerName=%ServerName%) Else (set ServerName=%1)
if "%~2"=="" (set inFilePath=%inFilePath%) Else (set inFilePath=%~2)
if "%~3"=="" (set LogPath=%LogPath%) Else (set LogPath=%~3)
if "%4"=="" (set UserID=%UserID%) Else (set UserID=%4)
if "%5"=="" (set Password=%Password%) Else (set Password=%5)
if "%~6"=="" (set sqlserverDataPath=%sqlserverDataPath%) Else (set sqlserverDataPath=%~6)
if "%7"=="" (set Database=%Database%) Else (set Database=%7)

REM ログ出力
Set sqllog="%LogPath%\RestoreSql.log"
Set cmdlog="%LogPath%\RestoreBat.log"

REM 起動パラメータ
echo DB setup start. > %cmdlog%
echo ServerName=%ServerName% >> %cmdlog%
echo inFilePath=%inFilePath% >> %cmdlog%
echo UserID=%UserID% >> %cmdlog%
echo sqlserverDataPath=%sqlserverDataPath% >> %cmdlog%
echo Database=%Database% >> %cmdlog%

REM 復元開始
sqlcmd -S %ServerName% -U %UserID% -P %Password% -d "master" -o %sqllog% -Q "EXIT(USE [master] BEGIN TRY RESTORE DATABASE [%Database%] FROM DISK = N'%inFilePath%' WITH FILE = 1,  MOVE N'exchange' TO N'%sqlserverDataPath%\%Database%.mdf',  MOVE N'exchange_log' TO N'%sqlserverDataPath%\%Database%_log.ldf',  NOUNLOAD,  STATS = 5 SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"

REM PWSP-セキュリティ-ユーザー-削除
If %errorlevel%==0 (
   sqlcmd -S %ServerName% -U %UserID% -P %Password% -d "master" -o %sqllog% -Q "EXIT(USE [%Database%] BEGIN TRY DROP USER IF EXISTS [%UserID%] SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"
)

REM データベース-セキュリティ-ログイン更新・マッピング
If %errorlevel%==0 (
   sqlcmd -S %ServerName% -U %UserID% -P %Password% -d "master" -o %sqllog% -Q "EXIT(USE [Master] BEGIN TRY ALTER LOGIN [%UserID%] WITH PASSWORD=N'%Password%' , DEFAULT_DATABASE=[%Database%] ; USE [%Database%] CREATE USER [%UserID%] FOR LOGIN [%UserID%] ALTER USER [%UserID%] WITH DEFAULT_SCHEMA=[dbo] ALTER ROLE [db_owner] ADD MEMBER [%UserID%] ;  SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"
)

REM 接続確認
If %errorlevel%==0 (
   sqlcmd -S %ServerName% -U %UserID% -P %Password% -o %sqllog% -Q "EXIT(BEGIN TRY SELECT Getdate() SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"
)

REM 終了
echo DB setup Result=%errorlevel% >> %cmdlog%
exit /b %errorlevel%

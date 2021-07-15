@echo off
break on
set CWD=%~dp0
REM =============================================
REM データベースの復元
REM 起動パラメータ
REM 1:データベース名 2:復元ファイルパス 3:mdf/ldfのファイルフォルダ 4:サーバー名  5:ログファイルフォルダ 6:ユーザーID 7:パスワード
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

REM Dashboardユーザー
Set Database=PWSP
Set UserID=Dashboard_Admin
Set Password=P@ssW0rd

REM 入力ファイルパス
Set inFilePath=C:\sqlserver\data\PWSP.bak

REM ログ出力先
Set LogPath=%CWD%

REM mdf/ldfのファイル
Set sqlserverDataPath=C:\sqlserver\data

REM 起動パラメータチェック
if "%1"=="" (set Database=%Database%) Else (set Database=%1)
if "%~2"=="" (set inFilePath=%inFilePath%) Else (set inFilePath=%~2)
if "%~3"=="" (set sqlserverDataPath=%sqlserverDataPath%) Else (set sqlserverDataPath=%~3)
if "%4"=="" (set ServerName=%ServerName%) Else (set ServerName=%4)
if "%~5"=="" (set LogPath=%LogPath%) Else (set LogPath=%~5)
if "%6"=="" (set UserID=%UserID%) Else (set UserID=%6)
if "%7"=="" (set Password=%Password%) Else (set Password=%7)

REM ログ出力
Set sqllog="%LogPath%\RestoreSql.log"
Set cmdlog="%LogPath%\RestoreBat.log"

REM 起動パラメータ
echo DB setup start. > %cmdlog%
echo ServerName=%ServerName% >> %cmdlog%
echo Database=%Database% >> %cmdlog%
echo inFilePath=%inFilePath% >> %cmdlog%
echo UserID=%UserID% >> %cmdlog%
echo sqlserverDataPath=%sqlserverDataPath% >> %cmdlog%

REM 復元開始
sqlcmd -S %ServerName% -U %UserID% -P %Password% -d "master" -o %sqllog% -Q "EXIT(USE [master] BEGIN TRY RESTORE DATABASE [%Database%] FROM DISK = N'%inFilePath%' WITH FILE = 1,  MOVE N'pc' TO N'%sqlserverDataPath%\%Database%.mdf',  MOVE N'pc_log' TO N'%sqlserverDataPath%\%Database%_log.ldf',  NOUNLOAD,  STATS = 5 SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"

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

@echo off
break on
set CWD=%~dp0
REM =============================================
REM IDリセット
REM 起動パラメータ
REM 1:サーバー名 2:データベース名 3:ユーザーID 4:パスワード 5:ログ
REM --------------------------------
REM 動作
REM 1.IDリセット
REM =============================================

REM DBサーバー名
Set ServerName=localhost\PWSP
Set Database=exchange

REM Dashboardユーザー
Set UserID=Rtc_Admin
Set Password=P@ssW0rd

REM ログ出力先
Set LogPath=%CWD%

REM 起動パラメータチェック
if "%1"=="" (set ServerName=%ServerName%) Else (set ServerName=%1)
if "%2"=="" (set Database=%Database%) Else (set Database=%2)
if "%3"=="" (set UserID=%UserID%) Else (set UserID=%3)
if "%4"=="" (set Password=%Password%) Else (set Password=%4)
if "%~5"=="" (set LogPath=%LogPath%) Else (set LogPath=%~5)

REM ログ出力
Set cmdlog=%LogPath%\ResetIdBat.log
Set sqllog=%LogPath%\ResetIdSql.log

REM 起動パラメータ
echo ID Reset start. > %cmdlog%
echo ServerName=%ServerName% >> %cmdlog%
echo Database=%Database% >> %cmdlog%
echo UserID=%UserID% >> %cmdlog%

REM IDリセット
sqlcmd -S %ServerName% -U %UserID% -P %Password% -o %sqllog% -Q "EXIT(USE [%Database%] BEGIN TRY DBCC CHECKIDENT ('accounts', RESEED, 0); SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"

REM 終了
echo ID Reset Result=%errorlevel% >> %cmdlog%
exit /b %errorlevel%

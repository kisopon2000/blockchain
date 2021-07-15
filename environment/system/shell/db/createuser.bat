@echo off
break on
set CWD=%~dp0
set SysRootPath=%CWD%..\..\..\
REM =============================================
REM ログインユーザー作成
REM 起動パラメータ
REM 1:サーバー名 2:ユーザーID 3:パスワード 4:ログ
REM --------------------------------
REM 動作
REM 1.ユーザーを作成
REM =============================================

REM DBサーバー名
Set ServerName=localhost\PWSP

REM DBユーザー
Set UserID=Rtc_Admin
Set Password=P@ssW0rd

REM ログ出力先
Set LogPath=%CWD%

REM 起動パラメータチェック
if "%1"=="" (set ServerName=%ServerName%) Else (set ServerName=%1)
if "%2"=="" (set UserID=%UserID%) Else (set UserID=%2)
if "%3"=="" (set Password=%Password%) Else (set Password=%3)
if "%~4"=="" (set LogPath=%LogPath%) Else (set LogPath=%~4)

REM ログ出力
Set cmdlog=%LogPath%\CreateUserBat.log
Set sqllog=%LogPath%\CreateUserSql.log

REM 起動パラメータ
echo User Create start. > %cmdlog%
echo ServerName=%ServerName% >> %cmdlog%
echo UserID=%UserID% >> %cmdlog%

REM データベース-セキュリティ-ログイン-作成
sqlcmd -S %ServerName% -o %sqllog% -Q "EXIT(USE [Master] BEGIN TRY IF NOT EXISTS (SELECT * FROM sys.syslogins where name = N'%UserID%') CREATE LOGIN [%UserID%] WITH PASSWORD=N'%Password%',  DEFAULT_DATABASE=[master] , DEFAULT_LANGUAGE=[日本語], CHECK_EXPIRATION=OFF, CHECK_POLICY=ON ; ALTER SERVER ROLE [sysadmin] ADD MEMBER [%UserID%] ; SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"

REM VIEW SERVER STATE権限付与
If %errorlevel%==0 (
   sqlcmd -S %ServerName% -o %sqllog% -Q "EXIT(USE [master] BEGIN TRY GRANT VIEW SERVER STATE TO [%UserID%] ; SELECT 0 END TRY BEGIN CATCH SELECT ERROR_NUMBER(),ERROR_MESSAGE() END CATCH)"
)

REM 終了
echo User Create Result=%errorlevel% >> %cmdlog%
exit /b %errorlevel%

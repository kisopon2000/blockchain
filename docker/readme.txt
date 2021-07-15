=============================
 コンテナ/Docker環境構築手順
=============================

1. コンテナ/Dockerのインストール
   https://www.server-world.info/query?os=Windows_Server_2019&p=docker&f=1

2. 必要なファイルを用意 (これらはコンテナ内に配置される)
   ./docker/tools/win
    ・vc_redist.x86.exe (Runtime)
    ・vc_redist.x64.exe (Runtime)
    ・gvim*.exe (Vim)
    ・rewrite.msi (IIS Rewrite)
    ・requestRouter_amd64.msi (IIS Rewrite)
    ・mysql-connector-odbc-8.0.22-winx64.msi (MySQL用ODBCドライバー)
    ・msodbcsql.msi (SQL Server用ODBCドライバー)
    ・db_create_user.bat (SQL Server用ユーザー作成バッチ)
    ・sqlcmd (SQL Server用コマンド)
    ・database_enu (SQL Server Express 英語) ※2021/4時点は英語しか使えない
    ・database_jpn (SQL Server Express 日本語)
   ./archives
    ・system.zip (配置したいファイル群を一元化したZIPファイル)

3. ビルドイメージを作成
   cd <Build-Images.ps1が存在するパス(Dockerfileが存在するパス)>
   "Build-Images.ps1 -ImageName <イメージ名>"を実行。
   "docker images"を実行し、作成したイメージが存在することを確認(REPOSITORY名が上記イメージ名である)。

4. コンテナを起動
   "docker run --entrypoint powershell -it -p 8888:80 <REPOSITORY名>"でアクセス。
   8888はアクセス元(ホスト)のポート、80はアクセス先(コンテナ)のポート

5. Vimをインストール
   "gvim82.exe /S"でコンテナ内でインストールされる。
   ホスト側でMicrosoft.PowerShell_profile.ps1を用意し、以下を記入しておく。
   「set-alias vi 'C:\Program Files (x86)\Vim\vim82\vim.exe'」
   同ファイルをコンテナ内の「C:\Users\ContainerAdministrator\Documents\WindowsPowerShell」にコピー。
   "docker cp <プロファイルのパス> <コンテナID>:/Users\ContainerAdministrator\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
   "docker ps"により、当該イメージのNAMEを把握。
   "docker stop <上記のNAME>"により、当該コンテナを停止。
   "docker start <上記のNAME>"により、当該コンテナを再起動。(OS再起動と等価)
   "docker attach <上記のNAME>"により、当該コンテナに入る。
   これで「vi」コマンドでVimが使えることを確認できる。

6. IIS URL Rewriteをインストールするためのバージョン調整
   Get-ItemProperty -Path Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\InetStp
   MajorVersionが10である場合は以下を実施。
   Set-ItemProperty -Path Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\InetStp -Name MajorVersion -Value 9
   "docker stop <コンテナのNAME>"により、当該イメージを停止。
   "docker start <コンテナのNAME>"により、当該イメージを再起動。(OS再起動と等価)

7. IIS URL Rewriteをインストール
   コンテナ内で以下を実施。
   msiexec.exe /qn /i <rewrite.msiのフルパス>
   msiexec.exe /qn /i <requestRouter_amd64.msiのフルパス>
    ※MSIファイルはフルパスを指定しないと失敗する。
   以下を実行して、正常にインストールされていることを確認。
   Get-WmiObject Win32_Product | Select-Object Name,Vendor,Version,Caption | ForEach-Object {if($_.Name -like "*rewrite*"){ Write-Host $_ }}
   "*IIS URL Rewrite Module*"が表示されればよい。

8. IISセットアップ
   コンテナ内で以下を実施。
   iis-setup.ps1 -Site <サイト名> -StopSiteConflictPort 80

9. ODBCドライバーをインストール
   アプリ用コンテナ内で以下を実施。
   [MySQL]
    msiexec.exe /qn /i <mysql-connector-odbc-8.0.22-winx64.msiのフルパス>
     ※MSIファイルはフルパスを指定しないと失敗する。
    以下を実行して、正常にインストールされていることを確認。
    $HKLM = 2147483650
    $reg = [WMIClass]"ROOT\DEFAULT:StdRegProv"
    $Key = "SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers"
    $reg.EnumValues($HKLM, $Key) | % { $_.sNames | % {$_ + "`t" + $reg.getStringValue($HKLM, $Key, $_).sValue } }
    "MySQL ODBC * Driver      Installed"が表示されればよい。
   [SQL Server]
    msiexec.exe /quiet /passive /qn /i <msodbcsql.msiのフルパス> IACCEPTMSODBCSQLLICENSETERMS=YES
    以下を実行して、正常にインストールされていることを確認。
    $HKLM = 2147483650
    $reg = [WMIClass]"ROOT\DEFAULT:StdRegProv"
    $Key = "SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers"
    $reg.EnumValues($HKLM, $Key) | % { $_.sNames | % {$_ + "`t" + $reg.getStringValue($HKLM, $Key, $_).sValue } }
    "ODBC Driver * for SQL Server   Installed"が表示されればよい。

10.DBセットアップ
   [MySQL]
    以下からMySQL(バージョン8.0.22)をダウンロード
    https://dev.mysql.com/downloads/installer/
    ホストにインストール(インストーラーの設定はすべてデフォルトでよい。パスワードは任意。ここでは"Recho2000"とする)
    ホストの環境変数Pathに「C:\Program Files\MySQL\MySQL Server 8.0\bin」を追加。
    シェルにて以下を実行。
    mysql.exe -u root -p
    CREATE USER 'root'@'%' IDENTIFIED BY 'Rencho2000';
    GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
     ※新規ユーザーrootを作成。パスワードはRencho2000。外部からのアクセスを可能とする"%"権限とする。
       "select user, host from mysql.user;"で確認可能。
    これで、コンテナからホストへ、root/Rencho2000でアクセス可能となる。
    コンテナから接続するホストのIPアドレスは、コンテナ内で「ping <ホストのコンピューター名>」を実行して取得する。
   [SQL Server]
    DB(SQL Server)用コンテナをつくる。
    docker pull kkbruce/mssql-server-windows-express:windowsservercore-1809
    docker run -d -p 1433:1433 -e sa_password=Rencho2000 -e ACCEPT_EULA=Y -v "C:/docker/sqlserver/data:C:/sqlserver/data" kkbruce/mssql-server-windows-express:windowsservercore-1809
     ※詳細はTIPSの「SQL Serverのデータ永続化」を参照。
    コンテナ内で以下を実施。
    cd C:/docker/tools/win/database_en
    & .\SETUP.EXE /Q /ACTION=Install /IACCEPTSQLSERVERLICENSETERMS /FEATURES=SQLEngine,Conn /INSTANCENAME=PWSP /SECURITYMODE=SQL /SAPWD=Rencho2000 /NPENABLED=1 /TCPENABLED=1 /AGTSVCACCOUNT='NT AUTHORITY\NETWORK SERVICE' /SQLSVCACCOUNT='NT AUTHORITY\NETWORK SERVICE' /SQLSYSADMINACCOUNTS='BUILTIN\ADMINISTRATORS'
    .\db_create_user.bat <コンテナのIP>\PWSP
     ※コンテナのIPはTIPS参照。
       これで、ホストのSSMSから「<コンテナのIP>\PWSP」インスタンスへ、Dashboard_Admin/P@ssW0rdでアクセスできる。

11.ホストのブラウザから「http://localhost:8888」でアクセス。
   諸々の動作を確認できる。

12.コンテナイメージの保存
   "docker stop <コンテナのNAME>"により、当該コンテナを停止。
   "docker commit <保存したい既存コンテナのNAME> <任意の名前>"により、任意の名前でイメージをコピー＆保存。
   "docker images"により、上記の名前(REPOSITORY名)でイメージが追加されていることを確認。

13.Dockerイメージの搬出
   "docker save <上記のREPOSITORY名> -o <出力先ファイルパス(拡張子は.tar)>"

14.Dockerイメージの搬入 (構築したい環境で実施)
   "docker load -i <搬入したいイメージ(拡張子は.tar)>"


TIPS.
・docker rmiでエラーになるとき
  "docker ps -a"で停止しているコンテナ一覧を表示し、CONTAINER IDを確認。
  docker rm <CONTAINER ID>で削除してから、docker rmiする。
  docker rm <CONTAINER ID> <CONTAINER ID> <CONTAINER ID>…のように複数指定可能。

・docker-composeのインストール
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest "https://github.com/docker/compose/releases/download/1.23.2/docker-compose-Windows-x86_64.exe" -UseBasicParsing -OutFile $Env:ProgramFiles\docker\docker-compose.exe
   ※"1.23.2"はバージョンを指す。以下より最新の安定バージョンを確認して指定すればよい。
     https://github.com/docker/compose/releases

・docker-composeのビルドイメージ作成
  .\docker-compose.ymlを用意。
  .\DockerfileのRUNを調整。
  cd <ymlファイルと同フォルダ>
  docker-compose build

・Windows ContainerではMySQLのイメージは使えないため、SQL Server(microsoft/mssql-server-windows*)を使う。
  しかし、これもホストがWS2019(v1809)では2021/4時点で使えない…(run時にエラーが出る)。
  WS2019(v1809)のSQL Serverは、以下のカスタムイメージなら使用可能(Microsoftオフィシャル版では上記の通りエラーになる)。
  kkbruce/mssql-server-windows-express:windowsservercore-1809
  ホストからコンテナへのSSMS接続は以下を参照。
  http://kharuka2016.hatenablog.com/entry/2017/02/16/170009

・ホストからコンテナのIPアドレス取得
  docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' コンテナIDまたはコンテナ名

・ホストからコンテナのコマンド実行
  docker exec コンテナIDまたはコンテナ名 powershell -c "コンテナ内でのコマンド"

・SQL Serverのデータ永続化
  ①ホストにmdf,ldf保存先を作成(ここでは、"C:\docker\sqlserver\data"とする)
  ②docker run -d -p 1433:1433 -e sa_password=Rencho2000 -e ACCEPT_EULA=Y -v "C:/docker/sqlserver/data:C:/sqlserver/data" kkbruce/mssql-server-windows-express:windowsservercore-1809
    ※ここでは、コンテナ側は"C:/sqlserver/data"としている。
    ※"docker exec -it コンテナIDまたはコンテナ名 powershell"でコンテナ内にアクセスできる。
  ③コンテナ側でDBを作成する。そのとき、mdf,ldfの保存先を"C:/sqlserver/data"を指定する。
  ④コンテナ停止。データはホスト側の"C:\docker\sqlserver\data"に保存されている。
  ⑤再度コンテナを起動するときは以下を実行。
    docker run -d -p 1433:1433 -e sa_password=Rencho2000 -e ACCEPT_EULA=Y -e attach_dbs="[{'dbname':'test','dbFiles':['C:\\sqlserver\\data\\test.mdf','C:\\sqlserver\\data\\test_log.ldf']}]" -v "C:/docker/sqlserver/data:C:/sqlserver/data" kkbruce/mssql-server-windows-express:windowsservercore-1809
    ※dbFilesは「\\」を指定しないと(エラーは出ないが)失敗する。

・コンテナでのPWSPインスタンスへのDBアタッチ方法
  sqlcmd -E -S "localhost\PWSP" -Q "sp_attach_db 'DB名(e.g. test)','C:\\sqlserver\\data\\test.mdf','C:\\sqlserver\\data\\test_log.ldf'"

・コンテナでのDBデタッチ方法
  sqlcmd -E -S "localhost\PWSP" -Q "sp_detach_db 'DB名(e.g. test)'"

・kkbruce/mssql-server-windows-express:windowsservercore-1809をDockerfileのFROMに指定してdocker buildした場合、
  同DockerfileにWORKDIRを記載すると、docker runで起動した直後に即終了してしまう。これは謎…。

・ラッパー含めた処理手順
■db
C:\docker\Build-Image.ps1 -Dockerfile C:\docker\rtc\db\Dockerfile -ImageName rtc_db_image_test
docker run -d -p 1433:1433 -e sa_password=Rencho2000 -e ACCEPT_EULA=Y -v "C:/docker/sqlserver/data:C:/sqlserver/data" rtc_db_image_test
docker ps
docker cp C:\docker\rtc\wrapper\pc.bak 70d3824d5a20:/sqlserver/pc.bak
docker exec 70d3824d5a20 powershell -c "Restore-DB -DBName pc -DBPath C:\sqlserver\pc.bak -DBDataDir C:\sqlserver\data"
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 70d3824d5a20

■app
C:\docker\Build-Image.ps1 -Dockerfile C:\docker\rtc\app\Dockerfile -ImageName rtc_app_image_test
docker run -d -p 8888:8080 rtc_app_image_test
docker ps
docker exec f7886baa9f0a powershell -c "Setup-DBConfig -DBType sqlserver -DBServer localhost\PWSP -DBName pc"

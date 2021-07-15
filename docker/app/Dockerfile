FROM microsoft/iis
LABEL maintainer="kimihiko.isobe.vg@fujifilm.com"
COPY /tools /archives/*.zip C:/setup/
RUN powershell.exe -noprofile -executionpolicy RemoteSigned -command "C:/setup/Setup-Container.ps1 -Product rtc -ArchiveFile system.zip"

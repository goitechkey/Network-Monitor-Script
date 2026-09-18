Option Explicit

Dim shell, scriptFolder, command
Set shell = CreateObject("WScript.Shell")
scriptFolder = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
command = "cmd.exe /c """ & scriptFolder & "Network-Monitor.cmd"" --service"
shell.Run command, 0, False

Option Explicit
Dim fso, shell, appDir, pythonw, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = "pythonw.exe"
cmd = "cmd /c cd /d """ & appDir & """ && """ & pythonw & """ ""main.py"""
shell.Run cmd, 0, False

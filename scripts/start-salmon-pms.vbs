Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wsl -d Ubuntu -u sannah bash -lc ""/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/scripts/start-salmon-pms.sh""", 0, False
Set WshShell = Nothing

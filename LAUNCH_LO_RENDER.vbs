Set WShell = CreateObject("WScript.Shell")
WShell.CurrentDirectory = "C:\Users\jjard\claude\video-bot-pipeline"
WShell.Run "conhost.exe cmd.exe /k C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe run_lo_render.py", 1, False

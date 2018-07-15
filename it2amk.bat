for /f "tokens=1,* delims= " %%a in ("%*") do set ALL_BUT_FIRST=%%b
set file="modules/%~1.it"
start /b /wait python3 it2amk.py %file% %ALL_BUT_FIRST%
start /b /wait AddMusicK music.smc
start /b /wait SPCs\%~1.spc
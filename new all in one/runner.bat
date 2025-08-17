@echo off
rem Change directory to the batch-file's own folder
pushd "%~dp0"

rem List of specific scripts to run
set "SCRIPTS=dices.py number_gussing.py blocks_bot.py red_green.py main.py"

rem Loop over each script in the list
for %%S in (%SCRIPTS%) do (
    echo Launching %%S…
    start "%%~nS" cmd /k python "%%S"
)

rem Return to original directory
popd

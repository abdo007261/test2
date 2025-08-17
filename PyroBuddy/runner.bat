@echo off
rem Change directory to the batch-file's own folder
pushd "%~dp0"

echo Starting bot.py...
start "Bot" cmd /k python bot.py

rem Return to original directory
popd
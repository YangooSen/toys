@echo off
chcp 65001 >nul
echo ============================================
echo  正在打包 exe，第一次运行需要几分钟，请等待
echo ============================================
pip install -r requirements.txt
pyinstaller --onefile --windowed --name 文件名整理工具 file_renamer.py
echo.
echo 打包完成！exe 文件在 dist 文件夹里。
pause

::设置中文编码
chcp 65001
set num=1
set total= 21
set /a ptr = 0
echo 启用时间：%date% %time%
echo 当时间为0时执行完毕
echo 欢迎使用! 
::循环时间
:chongfu
if %num% equ  %total% (exit)
set /a sec=(%total%-%num%)
echo 剩余执行次数%sec%
:: http请求（可以换成任意事件）
ping 123.45.67.89 -n 1 -w 30>nul
python ./client.py %ptr%
echo %ptr%
set /a num+=1
set /a ptr+=4000
goto chongfu
pause

import schedule  
import time  
import subprocess  
from datetime import datetime  
def job():  
    # 执行你的脚本  
    subprocess.run(["python", "main.py"])  
    print(f"main.py 已被执行。当前时间：{datetime.now()}")  

def main():  
    # 获取并打印当前时间  
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    print(f"定时程序已经在 {current_time} 开始运行，将在规定时间自动执行脚本。\n")  
    print("按 Ctrl + C 退出程序\n")  
  
    # 设置定时任务  
    schedule.every().day.at("11:00").do(job)  
      
    try:  
        # 循环执行任务  
        while True:  
            schedule.run_pending()  
            time.sleep(1)  
    except KeyboardInterrupt:  
        # 捕获 Ctrl + C 中断信号  
        print("接收到中断信号，程序将在下一次循环结束后停止。")  
    finally:  
        print("定时程序已停止运行。") 

if __name__ == "__main__":  
    main()
 # type: ignore
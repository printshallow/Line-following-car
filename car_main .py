# =====================================================
# K210 黑块识别程序（优化版）
# =====================================================

import sensor,image,lcd,time,gc
from machine import UART
from fpioa_manager import fm

# =====================================================
# 黑色阈值（根据环境调整）
# =====================================================

black = (0, 60, -20, 20, -20, 20)
thresholds = [black]

# =====================================================
# 串口协议
# =====================================================

RecvCmd_Start = b'\x01'   # STM32开始识别
RecvCmd_Close = b'\x00'   # STM32停止识别

SendCmd_Not = b'\x10'     # 未检测到
SendCmd_Pos = b'\x11'     # 检测到

Flag_Start = 0

center_x = 0
center_y = 0

# =====================================================
# 摄像头初始化
# =====================================================

def Cam_Init():

    sensor.reset()

    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)

    # 使用全屏
    sensor.set_windowing((320,240))

    sensor.set_hmirror(1)
    sensor.set_vflip(1)

    # 关闭自动曝光
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)

    sensor.skip_frames(time=2000)


# =====================================================
# LCD初始化
# =====================================================

def LCD_Init():

    lcd.init(type=1)
    lcd.rotation(0)


# =====================================================
# 串口初始化
# =====================================================

def Uart_Init():

    fm.register(6,fm.fpioa.UART1_RX,force=True)
    fm.register(8,fm.fpioa.UART1_TX,force=True)

    uart = UART(UART.UART1,115200,read_buf_len=1024)

    return uart


# =====================================================
# 串口发送
# =====================================================

def Cmd_Send(cmd):

    uart.write(cmd)


# =====================================================
# 串口解析
# =====================================================

def Data_Analysis(data):

    global Flag_Start

    if not data:
        return

    if RecvCmd_Start in data:
        Flag_Start = 1

    elif RecvCmd_Close in data:
        Flag_Start = 0


# =====================================================
# 黑块识别
# =====================================================

def Find_Black(img):

    global center_x
    global center_y

    blobs = img.find_blobs(thresholds,
                           pixels_threshold=200,
                           area_threshold=200,
                           merge=True)

    if blobs:

        largest_blob = max(blobs,key=lambda b:b.pixels())

        center_x = largest_blob.cx()
        center_y = largest_blob.cy()

        img.draw_rectangle(largest_blob.rect(),color=(255,0,0))
        img.draw_cross(center_x,center_y,color=(0,255,0))

        return 1

    return 0


# =====================================================
# 发送识别结果
# =====================================================

def Send_Result(found):

    if found == 0:

        Cmd_Send(SendCmd_Not)

    else:

        Cmd_Send(SendCmd_Pos)

        uart.write(center_x.to_bytes(2,'big'))
        uart.write(center_y.to_bytes(2,'big'))
        print("发送坐标:",center_x,center_y)

# =====================================================
# 主程序
# =====================================================

Cam_Init()
LCD_Init()

uart = Uart_Init()

clock = time.clock()

while True:

    clock.tick()

    img = sensor.snapshot()

    # 读取串口（只读1字节防卡死）
    data = uart.read(1)

    if data:

        Data_Analysis(data)

    if Flag_Start:

        found = Find_Black(img)

        Send_Result(found)

        Flag_Start = 0

        img.draw_string(20,20,"Detecting",color=(255,255,0),scale=2)

    else:

        img.draw_string(20,20,"Waiting",color=(0,255,255),scale=2)

    # 显示FPS
    img.draw_string(5,200,"FPS:%.1f"%clock.fps(),color=(255,0,0),scale=2)

    lcd.display(img)

    if clock.fps() < 10:
        gc.collect()

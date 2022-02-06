import datetime
import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser

import httpx
import toml
from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from MainUI import *
from SetUI import *
DETACHED_PROCESS = 0x00000008
IS_WIN32 = 'win32' in str(sys.platform).lower()

# 重写 subprocess.Popen 令其不弹出命令行窗口
def subprocess_popen(*args, **kwargs):
    if IS_WIN32:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
    retcode = subprocess.Popen(*args, **kwargs)
    return retcode
# 重写 subprocess.run 令其不弹出命令行窗口
def subprocess_run(*args, **kwargs):
    if IS_WIN32:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
    retcode = subprocess.run(*args, **kwargs)
    return retcode

pixivconf = """#Pixiv
method=w-md5,s-seg,https
pixiv.net
.pixiv.net
i.pximg.net
.pximg.net
pixivsketch.net
.pixivsketch.net
analytics.twitter.com
t.co
connect.facebook.net
"""

# 读取 subprocess_Popen 的 stdout
def output_reader(proc, outq):
    for line in iter(proc.stdout.readline, b''):
        outq.put(line.decode('utf-8'))

Status = "等待命令"

def setStatus(x):
    return "状态：" + x

def GetTPConfig():
    httpx.get()

# 主窗口
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.SettingWindow = SettingWindow()
        self.setupUi(self)
        self.StopButton.setEnabled(False)
        self.statusBar().showMessage(setStatus("等待命令"))

    # 窗口关闭前杀掉 dnscrypt-proxy 和 tcpioneer
    def closeEvent(self, event):
        subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe', shell=False)
        subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe', shell=False)

    # 激活设置窗口
    def ShowSettingWindow(self):
        self.SettingWindow.init()
        self.SettingWindow.show()

    # 打开博客页面
    def About(self):
        webbrowser.open("https://blog.xcwosjw.com")

    # 启动 tcpioneer 和 dnscrypt-proxy
    def StartTcpioneer(self):

        self.StartDT=Thread()
        self.StartDT.MessageBox.connect(self.EMessageBox)
        self.StartDT.start()

    # 错误信息弹窗
    def EMessageBox(self,str):
        QMessageBox.critical(self, '错误', str, QMessageBox.Yes, QMessageBox.Yes)

    # 停止 tcpioneer 和 dnscrypt-proxy
    def StopTcpioneer(self):
        self.statusBar().showMessage(setStatus("正在停止"))
        self.StopButton.setEnabled(False)
        global s_stop
        # 设置停止标识,终止线程
        s_stop = True

# 不想写注释了
class Thread(QThread):
    MessageBox = pyqtSignal(str)
    print("89")
    def run(self):
        print("888")
        MainWindow.StartButton.setEnabled(False)
        MainWindow.statusBar().showMessage(setStatus("读取配置"))
        try:
            with open('PixLCG.json', 'r') as PixLCGconf:
                JSON = PixLCGconf.read()
                ConfigJson = json.loads(JSON)
                PixLCGconf.close()
        except:
            self.MessageBox.emit("配置文件错误，使用默认配置！")
            ConfigJson = json.loads('{"IPV6": false, "Log": true, "CustomDNS": "", "DnscryptEnable": true, "DnscryptCustomPortEnable": false, "DnscryptCustomPort": "53"}')
        Dnscryptconf = toml.load("bin\dnscrypt-proxy.toml")
        if ConfigJson["DnscryptEnable"]:
            Dnscryptconf["listen_addresses"] = ['0.0.0.0:' + ConfigJson["DnscryptCustomPort"]]
        else:
            Dnscryptconf["listen_addresses"] = ['0.0.0.0:53']
        Dnscryptconf["ipv6_servers"] = ConfigJson["IPV6"]
        print(Dnscryptconf)
        MainWindow.statusBar().showMessage(setStatus("写入配置"))
        toml.dump(Dnscryptconf, open('bin\dnscrypt-proxy.toml', mode='w'))
        if os.path.exists('bin\default.conf'):
            os.remove('bin\default.conf')
        with open('bin\default.conf', 'a+') as Tcpioneerconf:
            Tcpioneerconf.write("log=2\n")
            Tcpioneerconf.write("ipv6=" + str(ConfigJson["IPV6"]) + "\n")
            if ConfigJson["DnscryptEnable"]:
                Tcpioneerconf.write("server=127.0.0.1:" + ConfigJson["DnscryptCustomPort"] + "\n")
            else:
                Tcpioneerconf.write("server=127.0.0.1:53" + "\n")
            Tcpioneerconf.write("Cloudflare=cf.xcwosjw.com" + "\n")
            Tcpioneerconf.write(pixivconf + "\n")
        if ConfigJson["Log"]:
            if os.path.exists("logs") != True:
                os.makedirs("logs")
            times = datetime.datetime.now().strftime('%m-%d-%H-%M')
            print(os.getcwd() + r"\bin")
            subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe',shell=False)
            subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe',shell=False)
            MainWindow.statusBar().showMessage(setStatus("初始化Dnscrypt。这需要一点时间"))
            Dnscrypt = subprocess_popen(os.getcwd() + r"\bin\dnscrypt-proxy.exe", stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, cwd=os.getcwd() + r"\bin")
            outq = queue.Queue()
            d = threading.Thread(target=output_reader, args=(Dnscrypt, outq))
            d.start()
            TcpioneerStarted = False
            with open("logs\\Dnscrypt-" + times + ".txt", 'a+') as DnscryptLog:
                global s_stop
                s_stop = False
                MainWindow.StopButton.setEnabled(True)
                while s_stop!=True:
                    try:
                        line = outq.get(block=False)
                        if '{0}'.format(line).find("rtt") != -1:
                            if TcpioneerStarted != True:
                                print("启动Tcpioneer")
                                MainWindow.statusBar().showMessage(setStatus("启动Tcpioneer"))
                                Tcpioneer = subprocess_popen(os.getcwd() + r"\bin\tcpioneer.exe",
                                                             stdout=subprocess.PIPE,
                                                             stderr=subprocess.STDOUT, cwd=os.getcwd() + r"\bin")
                                outqt = queue.Queue()
                                t = threading.Thread(target=output_reader, args=(Tcpioneer, outqt))
                                t.start()
                                TcpioneerStarted = False
                                with open("logs\\Tcpioneer-" + times + ".txt", 'a+') as TcpioneerLog:
                                    while s_stop!=True:
                                        try:
                                            line = outqt.get(block=False)
                                            if '{0}'.format(line).find("Service Start") != -1:
                                                if TcpioneerStarted != True:
                                                    MainWindow.statusBar().showMessage(setStatus("Tcpioneer启动成功"))
                                                    TcpioneerStarted = True
                                                    MainWindow.statusBar().showMessage(setStatus("服务运行中"))
                                            print('{0}'.format(line), end='')
                                            TcpioneerLog.write('{0}'.format(line))
                                        except queue.Empty:
                                            print("Empty")
                                        time.sleep(0.3)
                                subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe', shell=False)
                                subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe', shell=False)
                                MainWindow.statusBar().showMessage(setStatus("进程退出中"))
                                MainWindow.StartButton.setEnabled(True)
                                MainWindow.statusBar().showMessage(setStatus("等待命令"))
                                t.join()
                                TcpioneerLog.close()
                        elif '{0}'.format(line).find(
                                "Only one usage of each socket address (protocol/network address/port) is normally permitted.") != -1:
                            self.MessageBox.emit("53端口被占用!请检查是否有进程占用53端口，或使用自定义端口。")
                            break
                        print('{0}'.format(line), end='')
                        DnscryptLog.write('{0}'.format(line))
                    except queue.Empty:
                        print("Empty")
                    time.sleep(0.3)
            d.join()
            DnscryptLog.close()
        else:
            times = datetime.datetime.now().strftime('%m-%d-%H-%M')
            print(os.getcwd() + r"\bin")
            subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe',shell=False)
            subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe',shell=False)
            MainWindow.statusBar().showMessage(setStatus("初始化Dnscrypt。这需要一点时间"))
            Dnscrypt = subprocess_popen(os.getcwd() + r"\bin\dnscrypt-proxy.exe", stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, cwd=os.getcwd() + r"\bin")
            outq = queue.Queue()
            d = threading.Thread(target=output_reader, args=(Dnscrypt, outq))
            d.start()
            TcpioneerStarted = False
            s_stop = False
            MainWindow.StopButton.setEnabled(True)
            while s_stop!=True:
                print(s_stop)
                if s_stop:
                    subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe',shell=False)
                    subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe',shell=False)
                    MainWindow.statusBar().showMessage(setStatus("进程退出中"))
                    MainWindow.StartButton.setEnabled(True)
                    MainWindow.statusBar().showMessage(setStatus("等待命令"))
                    break
                try:
                    line = outq.get(block=False)
                    if '{0}'.format(line).find("rtt") != -1:
                        if TcpioneerStarted != True:
                            print("启动Tcpioneer")
                            MainWindow.statusBar().showMessage(setStatus("启动Tcpioneer"))
                            Tcpioneer = subprocess_popen(os.getcwd() + r"\bin\tcpioneer.exe",
                                                         stdout=subprocess.PIPE,
                                                         stderr=subprocess.STDOUT, cwd=os.getcwd() + r"\bin")
                            outqt = queue.Queue()
                            t = threading.Thread(target=output_reader, args=(Tcpioneer, outqt))
                            t.start()
                            TcpioneerStarted = False
                            while s_stop!=True:
                                print(s_stop)
                                if s_stop:
                                    subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe',shell=False)
                                    subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe',shell=False)
                                    break
                                try:
                                    line = outqt.get(block=False)
                                    if '{0}'.format(line).find("Service Start") != -1:
                                        if TcpioneerStarted != True:
                                            MainWindow.statusBar().showMessage(setStatus("Tcpioneer启动成功"))
                                            TcpioneerStarted = True
                                            MainWindow.statusBar().showMessage(setStatus("服务运行中"))
                                    print('{0}'.format(line), end='')
                                except queue.Empty:
                                    print("Empty")
                                time.sleep(0.3)
                            t.join()
                    elif '{0}'.format(line).find(
                            "Only one usage of each socket address (protocol/network address/port) is normally permitted.") != -1:
                        self.MessageBox.emit("53端口被占用!请检查是否有进程占用53端口，或使用自定义端口。")
                        subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe',shell=False)
                        subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe',shell=False)
                        MainWindow.statusBar().showMessage(setStatus("进程退出中"))
                        MainWindow.StartButton.setEnabled(True)
                        MainWindow.statusBar().showMessage(setStatus("等待命令"))
                        break
                    print('{0}'.format(line), end='')
                except queue.Empty:
                    print("Empty")
                time.sleep(0.3)
        d.join()






# 设置窗口
class SettingWindow(QMainWindow, Ui_SettingWindow):
    def init(self):
        super(SettingWindow, self).__init__()
        self.setupUi(self)
        self.LoadConfig()

    def SaveConfig(self):
        Config = {}
        Config["IPV6"] = self.IPV6.isChecked()
        Config["Log"] = self.Log.isChecked()
        if self.CustomDNS.isChecked():
            if self.DNSEdit.text().find(":") != -1:
                Config["CustomDNS"] = self.DNSEdit.text()
                Config["DnscryptEnable"] = self.Dnscrypt.isChecked()
                Config["DnscryptCustomPortEnable"] = self.CustomPort.isChecked()
                Config["DnscryptCustomPort"] = self.PortEdit.text()
            else:
                QMessageBox.warning(self, '警告', '自定义DNS必须包含端口。例：8.8.8.8:53', QMessageBox.Yes, QMessageBox.Yes)
                return
        else:
            Config["CustomDNS"] = self.DNSEdit.text()
            Config["DnscryptEnable"] = self.Dnscrypt.isChecked()
            Config["DnscryptCustomPortEnable"] = self.CustomPort.isChecked()
            Config["DnscryptCustomPort"] = self.PortEdit.text()
        ConfigJson = json.dumps(Config)
        print(ConfigJson)
        with open('PixLCG.json', 'w') as PixLCGconf:
            PixLCGconf.write(ConfigJson)
            PixLCGconf.close()
        self.close()

    def LoadConfig(self):
        try:
            with open('PixLCG.json', 'r') as PixLCGconf:
                JSON = PixLCGconf.read()
                if JSON != "":
                    ConfigJson = json.loads(JSON)
                else:
                    return
                PixLCGconf.close()
            self.IPV6.setChecked(ConfigJson['IPV6'])
            self.Log.setChecked(ConfigJson['Log'])
            if ConfigJson["DnscryptEnable"]:
                self.CustomDNS.setChecked(False)
                self.DNSEdit.setReadOnly(True)
            else:
                self.CustomDNS.setChecked(True)
                self.DNSEdit.setReadOnly(False)
            self.DNSEdit.setText(ConfigJson["CustomDNS"])
            self.Dnscrypt.setChecked(ConfigJson["DnscryptEnable"])
            self.CustomPort.setChecked(ConfigJson["DnscryptCustomPortEnable"])
            self.PortEdit.setText(ConfigJson["DnscryptCustomPort"])
        except:
            QMessageBox.critical(self, '错误', '读取配置发生错误！', QMessageBox.Yes, QMessageBox.Yes)

    def DNSClicked(self):
        if self.CustomDNS.isChecked():
            if self.CustomPort.isChecked():
                self.PortEdit.setEnabled(False)
                self.PortEdit.setReadOnly(True)
            self.DNSEdit.setEnabled(True)
            self.DNSEdit.setReadOnly(False)
            self.CustomPort.setEnabled(False)

        else:
            self.DNSEdit.setEnabled(False)
            self.DNSEdit.setReadOnly(True)
            self.CustomPort.setEnabled(True)
            if self.CustomPort.isChecked():
                self.PortEdit.setEnabled(True)
                self.PortEdit.setReadOnly(False)

    def CustomPortClicked(self):
        print("233")
        if self.CustomPort.isChecked():
            self.PortEdit.setEnabled(True)
            self.PortEdit.setReadOnly(False)
        else:
            self.PortEdit.setEnabled(False)
            self.PortEdit.setReadOnly(True)

    def CancelSaveConfig(self):
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = MainWindow()
    MainWindow.show()
    MainWindow.setFixedSize(MainWindow.width(), MainWindow.height())
    subprocess_run('taskkill /f /im %s' % 'dnscrypt-proxy.exe', shell=False)
    subprocess_run('taskkill /f /im %s' % 'tcpioneer.exe', shell=False)
    sys.exit(app.exec_())

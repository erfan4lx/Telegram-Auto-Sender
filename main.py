import sys
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QProgressDialog
)
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox , QTableWidgetItem
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QTimer
from panel import Ui_MainWindow
from qasync import QEventLoop, asyncSlot
from func import telegram_panel
from code_dialog import CodeDialog, AsyncMessageBox
from pyrogram import (Client,errors,enums,types)
from pyrogram.raw import functions
import os, random, shutil, time, traceback , re
from datetime import datetime
from pymongo import MongoClient
os.makedirs('data', exist_ok=True)
os.makedirs('account', exist_ok=True)
os.makedirs('delete', exist_ok=True)


Status = False
sends_task = []


mongo = MongoClient("mongodb://localhost:27017")

db = mongo["tbch"]

mong_account = db["account"]
{
    "phone":str,
    "oks":int,
    "bads":int,
    "floodwait":int,
    "lastsend":int,
    "numberjoinnow":int
}
mong_banner = db["banner"]
{
    "name":str,
    "text":str
}
mong_join = db["join"]
{
    "phone":str,
    "link":str,
    "time":int
}
mong_config = db["config"]
{
    "config":int,
    "sendtime":int,
    "acctime":int,
    "rest":int,
    "lastsend":int,
    "status":bool
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        
        
        self.ui.setupUi(self)
        self.setFixedSize(self.size())
        self.acclistupdate()
        self.ui.add_account.clicked.connect(self.add_account_proc)
        self.ui.remove_account_bot.clicked.connect(self.remove_account)
        self.ui.update_number_bot.clicked.connect(self.acclistupdate)
        self.ui.tab_account.currentChanged.connect(self.update_list_tab)
        self.ui.pushButton.clicked.connect(self.Joinall)
        self.ui.pushButton_2.clicked.connect(self.Joinone)
        self.ui.pushButton_3.clicked.connect(self.Joinclear)
        self.ui.add_banner_button.clicked.connect(self.add_banner)
        self.ui.show_banner_button.clicked.connect(self.show_banner)
        self.ui.delete_banner_button.clicked.connect(self.delete_banner)
        self.ui.save_intervals_button.clicked.connect(self.save_intervals)
        self.ui.toggle_auto_send_button.clicked.connect(self.toggle_auto_send)
        self.ui.generate_stats_button.clicked.connect(self.generate_stats)
        
        
        
        global Status
        x = mong_config.find_one({"config":0})
        if x:
            Status = x["status"]
            self.ui.auto_send_status_label.setText("Auto-Send: " + (x["status"] and "ON" or "OFF"))


    
    
    
    def update_list_tab(self, index):
        if index == 0:
            r = telegram_panel.list_accounts()
            self.ui.list_account_ac.clear()
            self.ui.list_account_ac.addItems(r)
            self.ui.lcdNumber.display(len(r))
        if index == 1:
            r = telegram_panel.list_accounts()
            self.ui.comboBox.clear()
            self.ui.comboBox.addItems(r)
        if index == 2:
            unique_names = mong_banner.distinct('name')
            self.ui.banner_list.clear()
            self.ui.banner_list.addItems(unique_names)
        
        if index == 3:
            x = mong_config.find_one({"config":0})
            self.ui.send_interval_current.setText("Current: "+str(x["sendtime"]))
            self.ui.account_interval_current.setText("Current: "+str(int(x["acctime"] / 60)))
            self.ui.rest_interval_current.setText("Current: "+str(int(x["rest"] / 60)))
            self.ui.send_interval_spinbox.setValue(int(x["sendtime"]))
            self.ui.account_interval_spinbox.setValue(int(x["acctime"] / 60))
            self.ui.rest_interval_spinbox.setValue(int(x["rest"] / 60))

        if index == 4:
            x = mong_config.find_one({"config":0})
            self.ui.auto_send_status_label.setText("Auto-Send: "+str(x["status"] and "ON" or "OFF"))
        return
    
    
    
    @asyncSlot()
    async def ask_code_dialog(self, title, label):
        dlg = CodeDialog(title, label, self)
        dlg.setModal(True)
        dlg.show()
        while dlg.result() == 0:  # QDialog.DialogCode.Rejected = 0, Accepted = 1
            await asyncio.sleep(0.1)

        if dlg.result() == 1:
            return dlg.get_value(), True
        else:
            return "", False
    
    
    @asyncSlot()
    async def show_async_message(self, title, message, icon=QMessageBox.Icon.Information):
        dlg = AsyncMessageBox(title, message, icon, self)
        dlg.show()

        while dlg.result is None:
            await asyncio.sleep(0.05)

        return dlg


    def do_long_task(self):
        dlg = QProgressDialog("Processing ...", None, 0, 0, self)
        dlg.setWindowTitle("Please wait.")
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)
        dlg.show()
        return dlg


    @asyncSlot()
    async def add_account_proc(self):
        phone = self.ui.account_input_add.text().strip()

        if len(phone) < 4:
            # QMessageBox.critical(self, "Wrong", "Phone number is too short.")
            await self.show_async_message("Wrong", "Phone number is too short.", icon=QMessageBox.Icon.Critical)

            return

        if not phone.startswith("+") or not phone[1:].isdigit():
            # QMessageBox.critical(self, "Wrong", "Phone number must start with '+' and contain only digits after it.")
            await self.show_async_message("Wrong", "Phone number must start with '+' and contain only digits after it.", icon=QMessageBox.Icon.Critical)
            return

        if phone == "+123456789":
            # QMessageBox.critical(self, "Wrong", "Sample phone number is not allowed.")
            await self.show_async_message("Wrong", "Sample phone number is not allowed.", icon=QMessageBox.Icon.Critical)
            return

        dlg = self.do_long_task()
        r = await telegram_panel.add_account(phone)
        dlg.close()

        if not r["status"]:
            # QMessageBox.critical(self, "Error", r["message"])
            await self.show_async_message("Error", str(r["message"]), icon=QMessageBox.Icon.Critical)
            return

        # ورود کد
        for _ in range(3):
            # text, ok = QInputDialog.getText(self, "Account login code", "Enter the 5-digit code:")
            text, ok = await self.ask_code_dialog( "Account login code", "Enter the 5-digit code:")
            for _ in range(10):
                if not ok:
                    break
                if text.isdigit() and len(text) == 5:
                    break
                else:
                    # text, ok = QInputDialog.getText(self, "Account login code", "Enter the 5-digit code:")
                    text, ok = await self.ask_code_dialog( "Account login code", "Enter the 5-digit code:")

            if not ok:
                await telegram_panel.cancel_acc(r["cli"], r["phone"])
                # QMessageBox.critical(self, "Error", "Canceled by user.")
                await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
                return

            dlg = self.do_long_task()
            rs = await telegram_panel.get_code(r["cli"], r["phone"], r["code_hash"], text)
            dlg.close()

            if rs["status"]:
                # QMessageBox.information(self, "Success", rs["message"])
                await self.show_async_message("Success", rs["message"], icon=QMessageBox.Icon.Information)
                telegram_panel.make_json_data(r["phone"], r["api_id"], r["api_hash"], r["proxy"], "")
                mong_account.insert_one({"phone":r["phone"],"oks":0,"bads":0,"floodwait":0,"lastsend":0,"numberjoinnow":0})
                return

            if rs["message"] == "invalid_code":
                # QMessageBox.critical(self, "Error", "Invalid code.")
                await self.show_async_message("Error", "Invalid code.", icon=QMessageBox.Icon.Critical)
                continue

            if rs["message"] == "FA2":
                for _ in range(3):
                    # text, ok = QInputDialog.getText(self, "Account password", "Enter the password:")
                    text, ok = await self.ask_code_dialog("Account password", "Enter the password:")
                    if not ok:
                        await telegram_panel.cancel_acc(r["cli"], r["phone"])
                        # QMessageBox.critical(self, "Error", "Canceled by user.")
                        await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
                        return

                    dlg = self.do_long_task()
                    rsp = await telegram_panel.get_password(r["cli"], r["phone"], text)
                    dlg.close()

                    if rsp["status"]:
                        # QMessageBox.information(self, "Success", rsp["message"])
                        await self.show_async_message("Success", rsp["message"], icon=QMessageBox.Icon.Information)
                        telegram_panel.make_json_data(r["phone"], r["api_id"], r["api_hash"], r["proxy"], text)
                        mong_account.insert_one({"phone":r["phone"],"oks":0,"bads":0,"floodwait":0,"lastsend":0,"numberjoinnow":0})
                        return

                    if rsp["message"] == "invalid_password":
                        # QMessageBox.critical(self, "Error", "Invalid password.")
                        await self.show_async_message("Error", "Invalid password.", icon=QMessageBox.Icon.Critical)
                        continue
                    else:
                        # QMessageBox.critical(self, "Error", rsp["message"])
                        await self.show_async_message("Error", rsp["message"], icon=QMessageBox.Icon.Critical)
                        return

            if rs["message"]:
                # QMessageBox.critical(self, "Error", rs["message"])
                await self.show_async_message("Error", rs["message"], icon=QMessageBox.Icon.Critical)
                return

        try:await telegram_panel.cancel_acc(r["cli"], r["phone"])
        except:pass
        # QMessageBox.critical(self, "Error", "Canceled by user.")
        await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
        return

    def remove_account(self):
        phone = self.ui.remove_account_input.text().strip()
        if phone in telegram_panel.list_accounts():
            telegram_panel.remove_account(phone)
            QMessageBox.information(self, "Success", "Account removed.")
        else:
            QMessageBox.critical(self, "Error", "Account not found.")
        return
    

    def acclistupdate(self,log=True):
        r = telegram_panel.list_accounts()
        self.ui.list_account_ac.clear()
        self.ui.list_account_ac.addItems(r)
        self.ui.lcdNumber.display(len(r))
        if not log:
            QMessageBox.information(self, "Success", "Account list updated.")
        return
    
    def extract_telegram_links(self,text):
        public_pattern = r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)|@([a-zA-Z0-9_]+)'
        private_pattern = r'(?:https?://)?t\.me/\+([a-zA-Z0-9_-]+)|(?:https?://)?t\.me/joinchat/([a-zA-Z0-9_-]+)'
        
        public_matches = re.findall(public_pattern, text, re.IGNORECASE)
        private_matches = re.findall(private_pattern, text, re.IGNORECASE)
        
        public_links = [f'@{m[0]}' if m[0] else f'@{m[1]}' for m in public_matches]
        private_links = []
        for m in private_matches:
            if m[0]:
                private_links.append(f't.me/+{m[0]}')
            elif m[1]:
                private_links.append(f't.me/+{m[1]}')
        
        all_links = public_links + private_links
        return all_links if all_links else []
    
    
    @asyncSlot()
    async def Joinall(self):
        links = self.ui.textEdit.toPlainText()
        if len(links) != 0:
            lslnk = self.extract_telegram_links(links)
            if lslnk:
                timesleep = self.ui.gap_count_spinbox.value()
                now = int(time.time())
                lsacc = telegram_panel.list_accounts()
                for acc in lsacc:
                    for link in lslnk:
                        mong_join.insert_one({"phone":acc,"link":link,"time":now})
                        now = now + int(timesleep*60)
                self.ui.textEdit.clear()
                
                # QMessageBox.information(self, "Success", "Links added to the queue.")
                await self.show_async_message("Success", "Links added to the queue.\nnumber of links: {}\nnumber of accounts: {}".format(len(lslnk),len(lsacc)), icon=QMessageBox.Icon.Information)
                return
            else:
                # QMessageBox.critical(self, "Error", "No links found.")
                await self.show_async_message("Error", "No links found.", icon=QMessageBox.Icon.Critical)
                return
        else:
            await self.show_async_message("Error", "No links found.", icon=QMessageBox.Icon.Critical)
            return

    @asyncSlot()
    async def Joinone(self):
        links = self.ui.textEdit.toPlainText()
        acc = self.ui.comboBox.currentText()
        if acc == "":
            # QMessageBox.critical(self, "Error", "No account selected.")
            await self.show_async_message("Error", "No account selected.", icon=QMessageBox.Icon.Critical)
            return
        if len(links) != 0:
            lslnk = self.extract_telegram_links(links)
            if lslnk:
                timesleep = self.ui.gap_count_spinbox.value()
                now = int(time.time())
                lsacc = telegram_panel.list_accounts()
                if acc in lsacc:
                    for link in lslnk:
                        mong_join.insert_one({"phone":acc,"link":link,"time":now})
                        now = now + int(timesleep*60)
                else:
                    # QMessageBox.critical(self, "Error", "Account not found.")
                    await self.show_async_message("Error", "Account not found.", icon=QMessageBox.Icon.Critical)
                    return
                self.ui.textEdit.clear()
                
                # QMessageBox.information(self, "Success", "Links added to the queue.")
                await self.show_async_message("Success", "Links added to the queue.\nnumber of links: {}\n account: {}".format(len(lslnk),acc), icon=QMessageBox.Icon.Information)
                return
            else:
                # QMessageBox.critical(self, "Error", "No links found.")
                await self.show_async_message("Error", "No links found.", icon=QMessageBox.Icon.Critical)
                return
        else:
            await self.show_async_message("Error", "No links found.", icon=QMessageBox.Icon.Critical)
            return
    
    def Joinclear(self):
        qos = QMessageBox.question(self, "Clear Queue", "Are you sure you want to clear the queue?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if qos == QMessageBox.StandardButton.No:            
            return
        mong_join.delete_many({})
        QMessageBox.information(self, "Success", "Queue cleared.")
        return
    
    def add_banner(self):
        name = self.ui.banner_name_input.text().strip()
        text = self.ui.banner_text_input.toPlainText().strip()
        if len(name) != 0 and len(text) != 0:
            if mong_banner.find_one({"name":name}):
                QMessageBox.critical(self, "Error", "Banner name already exists.")
                return
            else:
                mong_banner.insert_one({"name":name,"text":text})
                QMessageBox.information(self, "Success", "Banner added.")
                self.ui.banner_name_input.clear()
                self.ui.banner_text_input.clear()
                unique_names = mong_banner.distinct('name')
                self.ui.banner_list.clear()
                self.ui.banner_list.addItems(unique_names)
                return
        else:
            QMessageBox.critical(self, "Error", "Banner name or text is empty.")
            return
    def show_banner_message(self,parent,name,  message_text):
        dialog = QDialog(parent)
        dialog.setWindowTitle(name)
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setPlainText(message_text)
        text_edit.setReadOnly(True)
        text_edit.setMinimumHeight(300)
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec()    
        return
    
    def show_banner(self):
        selct = self.ui.banner_list.currentItem()
        if selct == None:
            QMessageBox.critical(self, "Error", "No banner selected.")
            return
        selct = selct.text()
        x = mong_banner.find_one({"name":selct})
        if x == None:
            QMessageBox.critical(self, "Error", "Banner not found.")
            return
        self.show_banner_message(self,selct,x["text"])
        
    def delete_banner(self):
        selct = self.ui.banner_list.currentItem()
        if selct == None:
            QMessageBox.critical(self, "Error", "No banner selected.")
            return
        selct = selct.text()
        x = mong_banner.find_one({"name":selct})
        if x == None:
            QMessageBox.critical(self, "Error", "Banner not found.")
            return
        mong_banner.delete_one({"name":selct})
        QMessageBox.information(self, "Success", "Banner deleted.")
        unique_names = mong_banner.distinct('name')
        self.ui.banner_list.clear()
        self.ui.banner_list.addItems(unique_names)
        return
    
    def save_intervals(self):
        sendtime = self.ui.send_interval_spinbox.value()
        acctime = self.ui.account_interval_spinbox.value()
        rest = self.ui.rest_interval_spinbox.value()
        mong_config.update_one({"config":0},{"$set":{"sendtime":sendtime,"acctime":acctime*60,"rest":rest*60}})
        QMessageBox.information(self, "Success", "Intervals saved.")
        self.ui.send_interval_current.setText("Current: "+str(int(sendtime)))
        self.ui.account_interval_current.setText("Current: "+str(int(acctime / 60)))
        self.ui.rest_interval_current.setText("Current: "+str(int(rest / 60)))
        return
    
    def toggle_auto_send(self):
        global Status
        x = mong_config.find_one({"config":0})
        if x["status"]:
            Status = False
            mong_config.update_one({"config":0},{"$set":{"status":False}})
            QMessageBox.information(self, "Success", "Auto-Send disabled.")
            self.ui.auto_send_status_label.setText("Auto-Send: OFF")
        else:
            Status = True
            mong_config.update_one({"config":0},{"$set":{"status":True}})
            QMessageBox.information(self, "Success", "Auto-Send enabled.")
            self.ui.auto_send_status_label.setText("Auto-Send: ON")
        return
    
    def generate_stats(self):
        lsacc = telegram_panel.list_accounts()
        numberjoin = mong_join.count_documents({})
        numberbanner = mong_banner.count_documents({})
        
        # Fetch account details
        accounts_data = []
        for doc in mong_account.find({}):
            phone = doc.get('phone', 'N/A')
            oks = doc.get('oks', 0)
            bads = doc.get('bads', 0)
            accounts_data.append((phone, oks, bads))
        
        # Sort by phone if needed (optional)
        accounts_data.sort(key=lambda x: x[0])
        
        # Build HTML for first table (main stats, no total)
        html_stats = f"""
        <h3>Statistics Report</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr><th style="text-align: left; padding: 8px;">Name</th><th style="text-align: right; padding: 8px;">Count</th></tr>
            <tr><td style="padding: 8px;">Accounts</td><td style="text-align: right; padding: 8px;">{len(lsacc)}</td></tr>
            <tr><td style="padding: 8px;">Links</td><td style="text-align: right; padding: 8px;">{numberjoin}</td></tr>
            <tr><td style="padding: 8px;">Banners</td><td style="text-align: right; padding: 8px;">{numberbanner}</td></tr>
        </table>
        """
        
        # Build HTML for second table (account details)
        html_accounts = "<h3>Account Details</h3><table border='1' style='border-collapse: collapse; width: 100%;'>"
        html_accounts += "<tr><th style='text-align: left; padding: 8px;'>Phone</th><th style='text-align: right; padding: 8px;'>Success</th><th style='text-align: right; padding: 8px;'>Fail</th></tr>"
        for phone, oks, bads in accounts_data:
            html_accounts += f"<tr><td style='padding: 8px;'>{phone}</td><td style='text-align: right; padding: 8px;'>{oks}</td><td style='text-align: right; padding: 8px;'>{bads}</td></tr>"
        html_accounts += "</table>"
        
        # Combine and set to QTextEdit
        full_html = html_stats + "<br>" + html_accounts
        self.ui.report_gen.clear()
        self.ui.report_gen.setHtml(full_html)
        self.ui.report_gen.setReadOnly(True)       
        return
    
     
    
    
    
    

async def tabchi_run(phone:str , send=False):
    try:
        global Status
        if Status == False:return
        print("Loading {}...".format(phone))
        data = telegram_panel.get_json_data(phone)
        proxy = await telegram_panel.get_proxy(data["proxy"])
        cli = Client('account/{}'.format(phone), data["api_id"], data["api_hash"], proxy=proxy[0])
        if Status == False:return
        await asyncio.wait_for(cli.connect() , 15)
        print("Connected to {}.".format(phone))
        if Status == False:return
        accdata = mong_account.find_one({"phone":phone})
        dataconfig = mong_config.find_one({"config":0})
        if accdata == None:
            mong_account.insert_one({"phone":phone,"oks":0,"bads":0,"floodwait":0,"lastsend":0,"numberjoinnow":0})
            accdata = mong_account.find_one({"phone":phone})
        
        await cli.invoke(functions.account.UpdateStatus(offline=False))
        
        if Status == False:return
        FloodJoin = False
        for mng in mong_join.find({"phone":phone}):
            if Status == False:break
            if FloodJoin :break
            now = int(time.time())
            if now > mng["time"]:
                print(phone,"Joining {}...".format(mng["link"]))
                if Status == False:break
                join = await telegram_panel.Join(cli,mng["link"])

                if len(join) != 3:
                    print(phone,"Failed to join the group.\n{}".format(join[0]))
                    mong_join.delete_one({"_id":mng["_id"]})
                    await asyncio.sleep(5)
                    continue
                if len(join) == 2:
                    print(phone,"FloodWait :",join[1])
                    mong_join.update_many({"phone":phone},{"$inc":{"time":int(join[1]) + random.randint(10,300)}})
                    FloodJoin = True
                print(phone,"[Joined] {}".format(mng["link"]))
                mong_join.delete_one({"_id":mng["_id"]})
                await asyncio.sleep(5)
        
        if send:
            print(phone,"Sending banner...")
            if Status == False:return
            if int(time.time()) > accdata["floodwait"]:
                async for dialog in cli.get_dialogs():
                    chat = dialog.chat
                    if chat.type in [enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
                        random_banner = mong_banner.aggregate([{ "$sample": { "size": 1 } }]).next()
                        if random_banner != None:
                            try:
                                await cli.send_message(chat.id, random_banner["text"][:4096],link_preview_options=types.LinkPreviewOptions(is_disabled=True))
                                mong_account.update_one({"phone":phone},{"$inc":{"oks":1}})
                                mong_account.update_one({"phone":phone},{"$set":{"lastsend":int(time.time())}})
                                print(phone,"[Sent]",chat.title, chat.id,"Banner",random_banner["name"])
                                
                                await asyncio.sleep(dataconfig["sendtime"])
                            except errors.FloodWait as e:
                                print(phone,"[FloodWait] :",e.value)
                                mong_account.update_one({"phone":phone},{"$set":{"floodwait":int(time.time()) + e.value + random.randint(10,300)}})
                                mong_account.update_one({"phone":phone},{"$inc":{"bads":1}})
                                print(phone,"FloodWait :",e.value)
                                break
                            except (errors.ChatWriteForbidden  , errors.ChatRestricted):
                                print(phone , "[ChatWriteForbidden] or [ChatRestricted]",chat.title, chat.id)
                                mong_account.update_one({"phone":phone},{"$inc":{"bads":1}})
                                await asyncio.sleep(5)
                                await cli.leave_chat(chat.id)
                            except errors.SlowmodeWait:
                                await asyncio.sleep(5)
                                print(phone , "[SlowmodeWait]",chat.title, chat.id)
                                mong_account.update_one({"phone":phone},{"$inc":{"bads":1}})
                            
        await cli.invoke(functions.account.UpdateStatus(offline=True))
        await cli.disconnect()
        print("Disconnected from {}.".format(phone))
        return

    except (errors.AuthKeyUnregistered,errors.UserDeactivated,errors.InputUserDeactivated,errors.PhoneNumberBanned,errors.Unauthorized,errors.SessionRevoked,errors.AuthKeyInvalid) as e:
        try:await cli.disconnect()
        except:pass
        try:shutil.move('account/{}.session'.format(phone), 'delete/{}.session'.format(phone))
        except:pass
        try:shutil.move('data/{}.json'.format(phone), 'delete/{}.json'.format(phone))
        except:pass
        print(phone,"Error:",e)
        print(phone,"Account deleted.") 
    except Exception as e:
        try:await cli.disconnect()
        except:pass
        print(phone,"Error:",e)
        traceback.print_exc()
        return

async def back_task():
    global Status
    x = mong_config.find_one({"config":0})
    if x == None:
        mong_config.insert_one({"config":0,"status":False,"sendtime":60,"acctime":1,"rest":4,"lastsend":0})
    print("Back Task Run")
    mong_config.update_one({"config":0},{"$set":{"status":False}})
    x = mong_config.find_one({"config":0})
    Status = x["status"]
    
    while True:
        print("Back Task Run refresh",int(time.time()))
        try:
            x = mong_config.find_one({"config":0})
            listacc = telegram_panel.list_accounts()
            
            if x["status"] == True:
                print("started Send")
                senddd = False
                for mng in mong_account.find({}):
                    print("DB account found:", mng["phone"])
                    if Status == False:break
                    if mng["phone"] not in listacc:
                        print("Skipping account (not in listacc):", mng["phone"])
                        continue
                    if int(time.time()) > mng["floodwait"] and int(time.time()) > x["lastsend"]:
                        try:
                            print(mng["phone"], "Start Task SEND")
                            await asyncio.wait_for(tabchi_run(mng["phone"],True), timeout=3600)
                            senddd = True
                        except Exception as e:  
                            print(mng["phone"],e)
                    else:
                        runcx = False
                        for mng in mong_join.find({"phone":mng["phone"]}):
                            if Status == False:break
                            if int(time.time()) > mng["time"]:
                                runcx = True
                                break
                        if runcx:
                            try:
                                print(mng["phone"], "Start Task JOIN")
                                await asyncio.wait_for(tabchi_run(mng["phone"],False), timeout=3600)
                                senddd = True
                            except Exception as e:  
                                print(mng["phone"],e)
                    await asyncio.sleep(x["acctime"])
                if senddd:
                    mong_config.update_one({"config":0},{"$set":{"lastsend":int(time.time())+x["rest"]}})
            await asyncio.sleep(10)
        except Exception as e:
            print("Back Task Error:",e)
            traceback.print_exc()
            await asyncio.sleep(10)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app = QApplication(sys.argv)
    app.setStyle("Windows")
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    QTimer.singleShot(0, lambda: asyncio.create_task(back_task()))
    with loop:
        # asyncio.create_task(back_task())
        loop.run_forever()

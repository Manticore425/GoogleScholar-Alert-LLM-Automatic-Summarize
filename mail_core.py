import imaplib
import email
from email.header import decode_header
import webbrowser
import os
import re
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from imapclient import IMAPClient
from email import message_from_bytes


def connect_to_email(server, account, password):
    mail = IMAPClient("imap.163.com", ssl=True, port=993) # 视情况修改
    mail.login(account, password)
    mail.id_({"name": "IMAPClient", "version": "2.1.0"}) # 对于163邮箱，这一行是必须的
    return mail


def fetch_emails(mail, folder="INBOX"):
    mail.select_folder(folder)
    # messages = mail.search(["ALL"])
    messages = mail.search(["UNSEEN"])
    return messages


def read_email(mail, email_id):
    # res, msg = mail.fetch(email_id, "(RFC822)")
    raw_message = mail.fetch([email_id], ['RFC822'])
    msg = message_from_bytes(raw_message[email_id][b'RFC822'])

    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding if encoding else "utf-8")
    from_ = msg.get("From")
    papers= []
    if "<scholaralerts-noreply@google.com>" in from_:
        body = None
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        if body:
            soup = BeautifulSoup(body, 'html.parser')
            for h3 in soup.find_all('h3', {'style': 'font-weight:normal;margin:0;font-size:17px;line-height:20px;'}):
                paper = {}

                title_tag = h3.find('a', class_='gse_alrt_title')
                if title_tag:
                    paper['title'] = title_tag.get_text()
                    link = title_tag['href']
                    pdf_link_1 = re.findall(r'url=([^&"]+\.pdf)', link)
                    pdf_link_2 = re.findall(r'url=([^&"]+/pdf/[^&"]*)', link)
                    paper['link'] = pdf_link_1[0] if pdf_link_1 else pdf_link_2[0] if pdf_link_2 else None

                author_source_tag = h3.find_next_sibling('div', {'style': 'color:#006621;line-height:18px'})
                paper['author_source'] = author_source_tag.get_text() if author_source_tag else None

                abstract_tag = h3.find_next_sibling('div', class_='gse_alrt_sni')
                paper['abstract'] = abstract_tag.get_text(separator=' ', strip=True) if abstract_tag else None

                papers.append(paper)
    mail.add_flags(email_id, ['\\Seen'])
    return papers

def send_email(host, email, to_email,password, html_file_path):
    mail_user = email
    from_email = email
    to_email = to_email
    mail_pwd = password
    message = MIMEMultipart()
    message['From'] = from_email
    message['To'] =  ", ".join(to_email)
    message['Subject'] = "Daily paper conclusion{}".format(time.strftime("%Y-%m-%d", time.localtime()))  # 主题
    with open(html_file_path, 'r', encoding='utf-8') as html_file:
        html_content = html_file.read()
    message.attach(MIMEText(html_content, 'html', 'utf-8'))
    try:
        smtpObj = smtplib.SMTP_SSL(host, 465) 
        print("Connected to SMTP server")
        smtpObj.set_debuglevel(0)
        smtpObj.login(mail_user,mail_pwd)  #完成身份认证
        print("Logged in successfully")
        smtpObj.sendmail(from_email, to_email, message.as_string())   
        smtpObj.quit()
        print("Email sent successfully.")    

    except smtplib.SMTPException as e:
        print(e)

def trans_dict_into_text(paper_dict):
    text = ""
    for key, value in paper_dict.items():
        text += f"{key}: {value}\n"
    return text


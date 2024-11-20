import imaplib
import email
from email.header import decode_header
import webbrowser
import os
import re
from bs4 import BeautifulSoup
import smtplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

def connect_to_email(server, account, password):
    mail = imaplib.IMAP4_SSL(server)
    mail.login(account, password)
    return mail


def fetch_emails(mail, folder="INBOX"):
    mail.select(folder)

    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()
    return email_ids


def read_email(mail, email_id):
    res, msg = mail.fetch(email_id, "(RFC822)")
    papers= []
    for response in msg:
        if isinstance(response, tuple):
            # 解析邮件
            msg = email.message_from_bytes(response[1])
            
            # 获取邮件主题
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                # 如果是字节，则根据编码解码
                subject = subject.decode(encoding if encoding else "utf-8")
            
            # 获取发件人信息
            from_ = msg.get("From")
            if "<scholaralerts-noreply@google.com>" in from_:
                print(f"主题: {subject}")
                print(f"发件人: {from_}")
                # 检查邮件内容是否是多部分的
                content_type = msg.get_content_type()
                body = msg.get_payload(decode=True).decode()
                
                soup = BeautifulSoup(body, 'html.parser')
                for h3 in soup.find_all('h3', {'style': 'font-weight:normal;margin:0;font-size:17px;line-height:20px;'}):
                    paper = {}
                    
                    # 提取论文标题
                    title_tag = h3.find('a', class_='gse_alrt_title')
                    if title_tag:
                        paper['title'] = title_tag.get_text()
                        link = title_tag['href']
                        pdf_link_1 = re.findall(r'url=([^&"]+\.pdf)', link)
                        pdf_link_2 = re.findall(r'url=([^&"]+/pdf/[^&"]*)', link)
                        
                        # 如果找到符合正则的主链接，保留；否则置为空
                        if pdf_link_1:
                            paper['link'] = pdf_link_1[0]
                        elif pdf_link_2:
                            paper['link'] = pdf_link_2[0]
                        else:
                            paper['link'] = None
                    
                    # 提取作者和来源
                    author_source_tag = h3.find_next_sibling('div', {'style': 'color:#006621;line-height:18px'})
                    if author_source_tag:
                        paper['author_source'] = author_source_tag.get_text()
                    
                    # 提取摘要
                    abstract_tag = h3.find_next_sibling('div', class_='gse_alrt_sni')
                    if abstract_tag:
                        paper['abstract'] = abstract_tag.get_text(separator=' ', strip=True)
                    
                    # 提取保存、分享等链接（可选）
                    links_tag = h3.find_next_sibling('div', {'style': 'width:auto'})
                    if links_tag:
                        share_links = []
                        for a in links_tag.find_all('a', href=True):
                            href = a['href']
                            # 使用正则表达式筛选符合条件的PDF链接
                            pdf_links_1 = re.findall(r'url=([^&"]+\.pdf)', href)
                            pdf_links_2 = re.findall(r'url=([^&"]+/pdf/[^&"]*)', href)
                            
                            # 如果找到匹配的链接，则将其添加到 share_links 中
                            if pdf_links_1:
                                share_links.extend(pdf_links_1)
                            if pdf_links_2:
                                share_links.extend(pdf_links_2)
                        
                        paper['share_links'] = share_links
                    papers.append(paper)
            else:
                pass
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
    message.attach(MIMEText(html_content, 'html'))
    try:
        smtpObj = smtplib.SMTP()   
        smtpObj.connect(host,25)   
        smtpObj.set_debuglevel(0)
        smtpObj.login(mail_user,mail_pwd)  #完成身份认证
       
        smtpObj.sendmail(from_email, to_email, message.as_string())   
        smtpObj.quit()    

    except smtplib.SMTPException as e:
        print(e)

def trans_dict_into_text(paper_dict):
    text = ""
    for key, value in paper_dict.items():
        text += f"{key}: {value}\n"
    return text


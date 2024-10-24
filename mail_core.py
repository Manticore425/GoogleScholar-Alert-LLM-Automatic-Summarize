import imaplib
import email
from email.header import decode_header
import webbrowser
import os
import re
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
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
            
            msg = email.message_from_bytes(response[1])
            
        
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            
        
            from_ = msg.get("From")
            if "<scholaralerts-noreply@google.com>" in from_:
                print(f"主题: {subject}")
                print(f"发件人: {from_}")
            
                content_type = msg.get_content_type()
                body = msg.get_payload(decode=True).decode()
                
                soup = BeautifulSoup(body, 'html.parser')
                for h3 in soup.find_all('h3', {'style': 'font-weight:normal;margin:0;font-size:17px;line-height:20px;'}):
                    paper = {}
                    
               
                    title_tag = h3.find('a', class_='gse_alrt_title')
                    if title_tag:
                        paper['title'] = title_tag.get_text()
                        link = title_tag['href']
                        pdf_link_1 = re.findall(r'url=([^&"]+\.pdf)', link)
                        pdf_link_2 = re.findall(r'url=([^&"]+/pdf/[^&"]*)', link)
                        
                    
                        if pdf_link_1:
                            paper['link'] = pdf_link_1[0]
                        elif pdf_link_2:
                            paper['link'] = pdf_link_2[0]
                        else:
                            paper['link'] = None
                    
      
                    author_source_tag = h3.find_next_sibling('div', {'style': 'color:#006621;line-height:18px'})
                    if author_source_tag:
                        paper['author_source'] = author_source_tag.get_text()
                    
       
                    abstract_tag = h3.find_next_sibling('div', class_='gse_alrt_sni')
                    if abstract_tag:
                        paper['abstract'] = abstract_tag.get_text(separator=' ', strip=True)
                    
                  
                    links_tag = h3.find_next_sibling('div', {'style': 'width:auto'})
                    if links_tag:
                        share_links = []
                        for a in links_tag.find_all('a', href=True):
                            href = a['href']
                           
                            pdf_links_1 = re.findall(r'url=([^&"]+\.pdf)', href)
                            pdf_links_2 = re.findall(r'url=([^&"]+/pdf/[^&"]*)', href)
                        
                            if pdf_links_1:
                                share_links.extend(pdf_links_1)
                            if pdf_links_2:
                                share_links.extend(pdf_links_2)
                        
                        paper['share_links'] = share_links
                    papers.append(paper)
            else:
                pass
    return papers

def send_email(host, email, to_email,password, body):
    mail_user = email
    from_email = email
    to_email = to_email
    mail_pwd = password
    
    message = MIMEText(body, 'plain', 'utf-8') 
    message['From'] = from_email
    message['To'] = to_email
    message['Subject'] = "Daily paper conclusion{}".format(time.strftime("%Y-%m-%d", time.localtime()))  # 主题
   
    try:
        smtpObj = smtplib.SMTP()   
        smtpObj.connect(host,25)   
        smtpObj.set_debuglevel(0)
        smtpObj.login(mail_user,mail_pwd)  
        smtpObj.sendmail(from_email, to_email, message.as_string())   
        smtpObj.quit()    

    except smtplib.SMTPException as e:
        print(e)

def trans_dict_into_text(paper_dict):
    text = ""
    for key, value in paper_dict.items():
        text += f"{key}: {value}\n"
    return text


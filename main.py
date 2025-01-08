from mail_core import connect_to_email, fetch_emails, read_email,send_email
import hydra
from omegaconf import DictConfig
from utils import Paper_query
from summary_core.arxiv_search import chat_arxiv_main
from summary_core.arxiv_search import Reader
from llama_cpp import Llama
from convert_html import clean_summary, convert_html
model_path = "" # gguf model is all you need
def trans_dict_into_text(paper_dict):
    text = ""
    for paper in paper_dict:
        text += f"标题: {paper['title']}\n"
        text += f"摘要: {paper['result']}\n"
        text+="_"*20
        text += "\n"
    return text

llm = Llama(
    model_path=model_path,
    n_gpu_layers=-1,  # 根据需要卸载到 GPU
    n_ctx=32768,       # 设置上下文窗口大小
    verbose=False,    # 禁用详细日志输出
)

@hydra.main(config_path="config", config_name="mail.yaml", version_base=None)
def main(cfg: DictConfig):
    arxiv_summary = []
    server = cfg.mail_server#接受邮箱的服务器
    account = cfg.mail_account#接受邮箱的账号
    password = cfg.mail_password#接受邮箱的密码
    mail_user = cfg.mail_user#中转邮箱的账号
    mail_pwd = cfg.mail_pwd#中转邮箱的密码
    receivers = cfg.receivers#目标递送邮箱的账号
    receivers = list(receivers)
    mail = connect_to_email(server=server, account=account, password=password)
    email_ids = fetch_emails(mail)
    for email_id in email_ids[-5:]:
        paper_titles = read_email(mail, email_id)
        if paper_titles != []:
            break
    mail.logout()
    if len(paper_titles) > 0:
        for paper_title in paper_titles:
            query = Paper_query(paper_title["title"])
            key_word = "deep learning"
            reader1 = Reader(key_word,"",llm=llm,args=query)
            reader1.key_word = key_word
            reader1.query = paper_title["title"]
            reader1.show_info()
            paper_list = reader1.get_arxiv_web(
            paper_title
            )
            result = reader1.summary_with_chat(paper_list)
            #result = translater.translate_text(result)
            print(result)
            arxiv_summary.append({"title":paper_title["title"],
                                  "result":result})
        
        output = trans_dict_into_text(arxiv_summary)
        output = convert_html(clean_summary(output))
        send_email('smtp.163.com', mail_user, receivers, mail_pwd, html_file_path=output)
        
        print(output)
    else:
        print("No Scholar emails, exit!")
        
if __name__ == "__main__":
    main()
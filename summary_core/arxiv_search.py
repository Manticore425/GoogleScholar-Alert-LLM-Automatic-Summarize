import argparse
import base64
import configparser
import datetime
import io
import json
import os
import re
from collections import namedtuple

# import arxiv
import fitz
import numpy as np
import openai

# 导入所需的库
import requests
import tenacity
import tiktoken
from bs4 import BeautifulSoup
from PIL import Image
import sys


from llama_cpp import Llama

class Paper:
    def __init__(self, path, title="", url="", abs="", authers=[]):
        # 初始化函数，根据pdf路径初始化Paper对象
        self.url = url  # 文章链接
        self.path = path  # pdf路径
        self.section_names = []  # 段落标题
        self.section_texts = {}  # 段落内容
        self.abs = abs
        self.title_page = 0
        self.title = title
        self.pdf = fitz.open(self.path)  # pdf文档
        self.parse_pdf()
        self.authers = authers
        self.roman_num = [
            "I",
            "II",
            "III",
            "IV",
            "V",
            "VI",
            "VII",
            "VIII",
            "IIX",
            "IX",
            "X",
        ]
        self.digit_num = [str(d + 1) for d in range(10)]
        self.first_image = ""

    def parse_pdf(self):
        self.pdf = fitz.open(self.path)  # pdf文档
        self.text_list = [page.get_text() for page in self.pdf]
        self.all_text = " ".join(self.text_list)
        self.section_page_dict = self._get_all_page_index()  # 段落与页码的对应字典
        print("section_page_dict", self.section_page_dict)
        self.section_text_dict = self._get_all_page()  # 段落与内容的对应字典
        self.section_text_dict.update({"title": self.title})
        self.section_text_dict.update({"paper_info": self.get_paper_info()})
        self.pdf.close()

    def get_paper_info(self):
        first_page_text = self.pdf[self.title_page].get_text()
        if "Abstract" in self.section_text_dict.keys():
            abstract_text = self.section_text_dict["Abstract"]
        else:
            abstract_text = self.abs
        first_page_text = first_page_text.replace(abstract_text, "")
        return first_page_text

    def get_image_path(self, image_path=""):
        """
        将PDF中的第一张图保存到image.png里面，存到本地目录，返回文件名称，供gitee读取
        :param filename: 图片所在路径，"C:\\Users\\Administrator\\Desktop\\nwd.pdf"
        :param image_path: 图片提取后的保存路径
        :return:
        """
        # open file
        max_size = 0
        image_list = []
        with fitz.Document(self.path) as my_pdf_file:
            # 遍历所有页面
            for page_number in range(1, len(my_pdf_file) + 1):
                # 查看独立页面
                page = my_pdf_file[page_number - 1]
                # 查看当前页所有图片
                images = page.get_images()
                # 遍历当前页面所有图片
                for image_number, image in enumerate(page.get_images(), start=1):
                    # 访问图片xref
                    xref_value = image[0]
                    # 提取图片信息
                    base_image = my_pdf_file.extract_image(xref_value)
                    # 访问图片
                    image_bytes = base_image["image"]
                    # 获取图片扩展名
                    ext = base_image["ext"]
                    # 加载图片
                    image = Image.open(io.BytesIO(image_bytes))
                    image_size = image.size[0] * image.size[1]
                    if image_size > max_size:
                        max_size = image_size
                    image_list.append(image)
        for image in image_list:
            image_size = image.size[0] * image.size[1]
            if image_size == max_size:
                image_name = f"image.{ext}"
                im_path = os.path.join(image_path, image_name)
                print("im_path:", im_path)

                max_pix = 480
                origin_min_pix = min(image.size[0], image.size[1])

                if image.size[0] > image.size[1]:
                    min_pix = int(image.size[1] * (max_pix / image.size[0]))
                    newsize = (max_pix, min_pix)
                else:
                    min_pix = int(image.size[0] * (max_pix / image.size[1]))
                    newsize = (min_pix, max_pix)
                image = image.resize(newsize)

                image.save(open(im_path, "wb"))
                return im_path, ext
        return None, None

    # 定义一个函数，根据字体的大小，识别每个章节名称，并返回一个列表
    def get_chapter_names(
        self,
    ):
        # # 打开一个pdf文件
        doc = fitz.open(self.path)  # pdf文档
        text_list = [page.get_text() for page in doc]
        all_text = ""
        for text in text_list:
            all_text += text
        # # 创建一个空列表，用于存储章节名称
        chapter_names = []
        for line in all_text.split("\n"):
            line_list = line.split(" ")
            if "." in line:
                point_split_list = line.split(".")
                space_split_list = line.split(" ")
                if 1 < len(space_split_list) < 5:
                    if 1 < len(point_split_list) < 5 and (
                        point_split_list[0] in self.roman_num
                        or point_split_list[0] in self.digit_num
                    ):
                        print("line:", line)
                        chapter_names.append(line)
                    # 这段代码可能会有新的bug，本意是为了消除"Introduction"的问题的！
                    elif 1 < len(point_split_list) < 5:
                        print("line:", line)
                        chapter_names.append(line)

        return chapter_names

    def get_title(self):
        doc = self.pdf  # 打开pdf文件
        max_font_size = 0  # 初始化最大字体大小为0
        max_string = ""  # 初始化最大字体大小对应的字符串为空
        max_font_sizes = [0]
        for page_index, page in enumerate(doc):  # 遍历每一页
            text = page.get_text("dict")  # 获取页面上的文本信息
            blocks = text["blocks"]  # 获取文本块列表
            for block in blocks:  # 遍历每个文本块
                if block["type"] == 0 and len(block["lines"]):  # 如果是文字类型
                    if len(block["lines"][0]["spans"]):
                        font_size = block["lines"][0]["spans"][0][
                            "size"
                        ]  # 获取第一行第一段文字的字体大小
                        max_font_sizes.append(font_size)
                        if font_size > max_font_size:  # 如果字体大小大于当前最大值
                            max_font_size = font_size  # 更新最大值
                            max_string = block["lines"][0]["spans"][0][
                                "text"
                            ]  # 更新最大值对应的字符串
        max_font_sizes.sort()
        print("max_font_sizes", max_font_sizes[-10:])
        cur_title = ""
        for page_index, page in enumerate(doc):  # 遍历每一页
            text = page.get_text("dict")  # 获取页面上的文本信息
            blocks = text["blocks"]  # 获取文本块列表
            for block in blocks:  # 遍历每个文本块
                if block["type"] == 0 and len(block["lines"]):  # 如果是文字类型
                    if len(block["lines"][0]["spans"]):
                        cur_string = block["lines"][0]["spans"][0][
                            "text"
                        ]  # 更新最大值对应的字符串
                        font_flags = block["lines"][0]["spans"][0][
                            "flags"
                        ]  # 获取第一行第一段文字的字体特征
                        font_size = block["lines"][0]["spans"][0][
                            "size"
                        ]  # 获取第一行第一段文字的字体大小
                        # print(font_size)
                        if (
                            abs(font_size - max_font_sizes[-1]) < 0.3
                            or abs(font_size - max_font_sizes[-2]) < 0.3
                        ):
                            # print("The string is bold.", max_string, "font_size:", font_size, "font_flags:", font_flags)
                            if len(cur_string) > 4 and "arXiv" not in cur_string:
                                # print("The string is bold.", max_string, "font_size:", font_size, "font_flags:", font_flags)
                                if cur_title == "":
                                    cur_title += cur_string
                                else:
                                    cur_title += " " + cur_string
                            self.title_page = page_index
                            # break
        title = cur_title.replace("\n", " ")
        return title

    def _get_all_page_index(self):
        # 定义需要寻找的章节名称列表
        section_list = [
            "Abstract",
            "Introduction",
            "Related Work",
            "Background",
            "Introduction and Motivation",
            "Computation Function",
            " Routing Function",
            "Preliminary",
            "Problem Formulation",
            "Methods",
            "Methodology",
            "Method",
            "Approach",
            "Approaches",
            # exp
            "Materials and Methods",
            "Experiment Settings",
            "Experiment",
            "Experimental Results",
            "Evaluation",
            "Experiments",
            "Results",
            "Findings",
            "Data Analysis",
            "Discussion",
            "Results and Discussion",
            "Conclusion",
            "References",
        ]
        # 初始化一个字典来存储找到的章节和它们在文档中出现的页码
        section_page_dict = {}
        # 遍历每一页文档
        for page_index, page in enumerate(self.pdf):
            # 获取当前页面的文本内容
            cur_text = page.get_text()
            # 遍历需要寻找的章节名称列表
            for section_name in section_list:
                # 将章节名称转换成大写形式
                section_name_upper = section_name.upper()
                # 如果当前页面包含"Abstract"这个关键词
                if "Abstract" == section_name and section_name in cur_text:
                    # 将"Abstract"和它所在的页码加入字典中
                    section_page_dict[section_name] = page_index
                # 如果当前页面包含章节名称，则将章节名称和它所在的页码加入字典中
                else:
                    if section_name + "\n" in cur_text:
                        section_page_dict[section_name] = page_index
                    elif section_name_upper + "\n" in cur_text:
                        section_page_dict[section_name] = page_index
        # 返回所有找到的章节名称及它们在文档中出现的页码
        return section_page_dict

    def _get_all_page(self):
        """
        获取PDF文件中每个页面的文本信息，并将文本信息按照章节组织成字典返回。

        Returns:
            section_dict (dict): 每个章节的文本信息字典，key为章节名，value为章节文本。
        """
        text = ""
        text_list = []
        section_dict = {}

        # 再处理其他章节：
        text_list = [page.get_text() for page in self.pdf]
        for sec_index, sec_name in enumerate(self.section_page_dict):
            print(sec_index, sec_name, self.section_page_dict[sec_name])
            if sec_index <= 0 and self.abs:
                continue
            else:
                # 直接考虑后面的内容：
                start_page = self.section_page_dict[sec_name]
                if sec_index < len(list(self.section_page_dict.keys())) - 1:
                    end_page = self.section_page_dict[
                        list(self.section_page_dict.keys())[sec_index + 1]
                    ]
                else:
                    end_page = len(text_list)
                print("start_page, end_page:", start_page, end_page)
                cur_sec_text = ""
                if end_page - start_page == 0:
                    if sec_index < len(list(self.section_page_dict.keys())) - 1:
                        next_sec = list(self.section_page_dict.keys())[sec_index + 1]
                        if text_list[start_page].find(sec_name) == -1:
                            start_i = text_list[start_page].find(sec_name.upper())
                        else:
                            start_i = text_list[start_page].find(sec_name)
                        if text_list[start_page].find(next_sec) == -1:
                            end_i = text_list[start_page].find(next_sec.upper())
                        else:
                            end_i = text_list[start_page].find(next_sec)
                        cur_sec_text += text_list[start_page][start_i:end_i]
                else:
                    for page_i in range(start_page, end_page):
                        #                         print("page_i:", page_i)
                        if page_i == start_page:
                            if text_list[start_page].find(sec_name) == -1:
                                start_i = text_list[start_page].find(sec_name.upper())
                            else:
                                start_i = text_list[start_page].find(sec_name)
                            cur_sec_text += text_list[page_i][start_i:]
                        elif page_i < end_page:
                            cur_sec_text += text_list[page_i]
                        elif page_i == end_page:
                            if sec_index < len(list(self.section_page_dict.keys())) - 1:
                                next_sec = list(self.section_page_dict.keys())[
                                    sec_index + 1
                                ]
                                if text_list[start_page].find(next_sec) == -1:
                                    end_i = text_list[start_page].find(next_sec.upper())
                                else:
                                    end_i = text_list[start_page].find(next_sec)
                                cur_sec_text += text_list[page_i][:end_i]
                section_dict[sec_name] = cur_sec_text.replace("-\n", "").replace(
                    "\n", " "
                )
        return section_dict


# 定义Reader类
class Reader:
    def __init__(
        self,
        key_word,
        query,
        root_path="./",
        gitee_key="",
        llm = None,
        sort=None,
        user_name="defualt",
        args=None,
    ):
        self.user_name = user_name  # 读者姓名
        self.key_word = key_word  # 读者感兴趣的关键词
        self.query = query  # 读者输入的搜索查询
        self.sort = sort  # 读者选择的排序方式
        self.args = args
        if args.language == "en":
            self.language = "English"
        elif args.language == "zh":
            self.language = "Chinese"
        else:
            self.language = "Chinese"
        self.root_path = root_path
        # 创建一个ConfigParser对象
        self.config = configparser.ConfigParser()
        # 读取配置文件
        self.config.read("apikey.ini")
        OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
        # 获取某个键对应的值

        self.chat_api_list = []

        # prevent short strings from being incorrectly used as API keys.
        self.chat_api_list = [
            api.strip() for api in self.chat_api_list if len(api) > 20
        ]
        self.llm = llm
        self.cur_api = 0
        self.file_format = args.file_format
        if args.save_image:
            self.gitee_key = self.config.get("Gitee", "api")
        else:
            self.gitee_key = ""
        self.max_token_num = 4096
        self.encoding = tiktoken.get_encoding("gpt2")

    # 定义一个函数，根据关键词和页码生成arxiv搜索链接
    def get_url(self, keyword, page):
        base_url = "https://arxiv.org/search/?"
        params = {
            "query": keyword,
            "searchtype": "title",  # 搜索所有字段
            "abstracts": "show",  # 显示摘要
            "order": "-announced_date_first",  # 按日期降序排序
            "size": 50,  # 每页显示50条结果
        }
        if page > 0:
            params["start"] = page * 50  # 设置起始位置
        return base_url + requests.compat.urlencode(params)

    # 定义一个函数，根据链接获取网页内容，并解析出论文标题
    def get_titles(self, url, days=1):
        titles = []
        # 创建一个空列表来存储论文链接
        links = []
        dates = []
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all(
            "li", class_="arxiv-result"
        )  # 找到所有包含论文信息的li标签
        today = datetime.date.today()
        last_days = datetime.timedelta(days=days)
        for article in articles:
            try:
                title = article.find(
                    "p", class_="title"
                ).text  # 找到每篇论文的标题，并去掉多余的空格和换行符
                title = title.strip()
                link = article.find("span").find_all("a")[0].get("href")
                date_text = article.find("p", class_="is-size-7").text
                date_text = (
                    date_text.split("\n")[0].split("Submitted ")[-1].split("; ")[0]
                )
                date_text = datetime.datetime.strptime(date_text, "%d %B, %Y").date()
                if today - date_text <= last_days:
                    titles.append(title.strip())
                    links.append(link)
                    dates.append(date_text)
                # print("links:", links)
            except Exception as e:
                print("error:", e)
                print("error_title:", title)
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)

        return titles, links, dates

    # 定义一个函数，根据关键词获取所有可用的论文标题，并打印出来
    def get_all_titles_from_web(self, keyword, page_num=1, days=1):
        title_list, link_list, date_list = [], [], []
        for page in range(page_num):
            url = self.get_url(keyword, page)  # 根据关键词和页码生成链接
            titles, links, dates = self.get_titles(url, days)  # 根据链接获取论文标题
            if not titles:  # 如果没有获取到任何标题，说明已经到达最后一页，退出循环
                break
            for title_index, title in enumerate(titles):  # 遍历每个标题，并打印出来
                print(page, title_index, title, links[title_index], dates[title_index])
            title_list.extend(titles)
            link_list.extend(links)
            date_list.extend(dates)
        print("-" * 40)
        return title_list, link_list, date_list

    def get_arxiv_web(self, datas):
        
        paper_list = []
        url = datas["link"]# the link of the pdf document
        if url == None:
            return paper_list
        title = datas["title"]
        filename = self.try_download_pdf(url, title)
        paper = Paper(
                path=filename,
                url=datas["link"][:32] ,
                title=title,
            )
        paper_list.append(paper)
        return paper_list

    def validateTitle(self, title):
        # 将论文的乱七八糟的路径格式修正
        rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
        new_title = re.sub(rstr, "_", title)  # 替换为下划线
        return new_title

    def download_pdf(self, url, title):
        response = requests.get(url)  # send a GET request to the url
        date_str = str(datetime.datetime.now())[:13].replace(" ", "-")
        path = (
            self.root_path
            + "pdf_files/"
            + self.validateTitle(self.args.query)[:10]
            + "-"
            + date_str
        )
        try:
            os.makedirs(path)
        except:
            pass
        filename = os.path.join(path, self.validateTitle(title)[:10] + ".pdf")
        with open(filename, "wb") as f:  # open a file with write and binary mode
            f.write(response.content)  # write the content of the response to the file
        return filename

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        stop=tenacity.stop_after_attempt(5),
        reraise=True,
    )
    def try_download_pdf(self, url, title):
        return self.download_pdf(url, title)

    def summary_with_chat(self, paper_list):
        htmls = []
        for paper_index, paper in enumerate(paper_list):
            # 第一步先用title，abs，和introduction进行总结。
            text = ""
            text += "Title:" + paper.title
            text += "Url:" + paper.url
            text += "Abstract:" + paper.abs
            text += "Paper_info:" + paper.section_text_dict["paper_info"]
            # intro
            text += list(paper.section_text_dict.values())[0]
            chat_summary_text = ""
            try:
                chat_summary_text = self.chat_summary(text=text)
            except Exception as e:
                print("summary_error:", e)
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                if "maximum context" in str(e):
                    current_tokens_index = (
                        str(e).find("your messages resulted in")
                        + len("your messages resulted in")
                        + 1
                    )
                    offset = int(
                        str(e)[current_tokens_index : current_tokens_index + 4]
                    )
                    summary_prompt_token = offset + 1000 + 150
                    chat_summary_text = self.chat_summary(
                        text=text, summary_prompt_token=summary_prompt_token
                    )

            htmls.append("## Paper:" + paper.title)
            htmls.append("\n\n\n")
            if "chat_summary_text" in locals():
                htmls.append(chat_summary_text)

            # 第二步总结方法：
            # TODO，由于有些文章的方法章节名是算法名，所以简单的通过关键词来筛选，很难获取，后面需要用其他的方案去优化。
           
            method_key = ""
            for parse_key in paper.section_text_dict.keys():
                if "method" in parse_key.lower() or "approach" in parse_key.lower():
                    method_key = parse_key
                    break
                
            chat_method_text = ""
            if method_key != "":
                text = ""
                method_text = ""
                summary_text = ""
                summary_text += "<summary>" + chat_summary_text
                # methods
                method_text += paper.section_text_dict[method_key]
                text = summary_text + "\n\n<Methods>:\n\n" + method_text
                # chat_method_text = self.chat_method(text=text)
                try:
                    chat_method_text = self.chat_method(text=text)
                except Exception as e:
                    print("method_error:", e)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)
                    if "maximum context" in str(e):
                        current_tokens_index = (
                            str(e).find("your messages resulted in")
                            + len("your messages resulted in")
                            + 1
                        )
                        offset = int(
                            str(e)[current_tokens_index : current_tokens_index + 4]
                        )
                        method_prompt_token = offset + 800 + 150
                        chat_method_text = self.chat_method(
                            text=text, method_prompt_token=method_prompt_token
                        )

                if "chat_method_text" in locals():
                    htmls.append(chat_method_text)
                # htmls.append(chat_method_text)
            else:
                chat_method_text = ""
            htmls.append("\n" * 4)

            # 第三步总结全文，并打分：
            conclusion_key = ""
            for parse_key in paper.section_text_dict.keys():
                if "conclu" in parse_key.lower():
                    conclusion_key = parse_key
                    break

            text = ""
            conclusion_text = ""
            summary_text = ""
            summary_text += (
                "<summary>"
                + chat_summary_text
                + "\n <Method summary>:\n"
                + chat_method_text
            )
            chat_conclusion_text = ""
            if conclusion_key != "":
                # conclusion
                conclusion_text += paper.section_text_dict[conclusion_key]
                text = summary_text + "\n\n<Conclusion>:\n\n" + conclusion_text
            else:
                text = summary_text
            # chat_conclusion_text = self.chat_conclusion(text=text)
            try:
                chat_conclusion_text = self.chat_conclusion(text=text)
            except Exception as e:
                print("conclusion_error:", e)
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                if "maximum context" in str(e):
                    current_tokens_index = (
                        str(e).find("your messages resulted in")
                        + len("your messages resulted in")
                        + 1
                    )
                    offset = int(
                        str(e)[current_tokens_index : current_tokens_index + 4]
                    )
                    conclusion_prompt_token = offset + 1000 + 1000
                    chat_conclusion_text = self.chat_conclusion(
                        text=text, conclusion_prompt_token=conclusion_prompt_token
                    )
            if "chat_conclusion_text" in locals():
                htmls.append(chat_conclusion_text)
            htmls.append("\n" * 4)

            # # 整合成一个文件，打包保存下来。
            date_str = str(datetime.datetime.now())[:13].replace(" ", "-")
            export_path = os.path.join(self.root_path, "export")
            if not os.path.exists(export_path):
                os.makedirs(export_path)
            mode = "w" if paper_index == 0 else "a"
            file_name = os.path.join(
                export_path,
                date_str
                + "-"
                + self.validateTitle(self.query)
                + "."
                + self.file_format,
            )
            self.export_to_markdown("\n".join(htmls), file_name=file_name, mode=mode)
            htmls = self.translate_text("\n".join(htmls))
            return htmls

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        stop=tenacity.stop_after_attempt(5),
        reraise=True,
    )
    def chat_conclusion(self, text, conclusion_prompt_token=800):
       
        text_token = len(self.encoding.encode(text))
        clip_text_index = int(
            len(text) * (self.max_token_num - conclusion_prompt_token) / text_token
        )
        clip_text = text[:clip_text_index]

        messages = [
            {
                "role": "system",
                "content": "You are a reviewer in the field of ["
                + self.key_word
                + "] and you need to critically review this article",
            },
            # chatgpt 角色
            {
                "role": "assistant",
                "content": "This is the <summary> and <conclusion> part of an English literature, where <summary> you have already summarized, but <conclusion> part, I need your help to summarize the following questions:"
                + clip_text,
            },
            # 背景知识，可以参考OpenReview的审稿流程
            {
                "role": "user",
                "content": """                 
                 7. Make the following summary.Be sure to use {} answers (proper nouns need to be marked in English).
                    - (1):What is the significance of this piece of work?
                    - (2):Summarize the strengths and weaknesses of this article in three dimensions: innovation point, performance, and workload.                   
                 Follow the format of the output later: 
                 7. Conclusion: \n\n
                    - (1):xxx;\n                     
                    - (2):Innovation point: xxx; Performance: xxx; Workload: xxx;\n                      
                 
                 Be sure to use {} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.               
                 """.format(
                    self.language, self.language
                ),
            },
        ]
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            # prompt需要用英语替换，少占用token。
            messages=messages,
        )
        """
        response = self.llm.create_chat_completion(
        messages=messages,
        max_tokens=1000,
        stream=False
        )
        result = ""
        for choice in response["choices"]:
            result += choice["message"]["content"]
        #print("method_result:\n", result)
        print(
            "prompt_token_used:",
            response["usage"]["prompt_tokens"],
            "completion_token_used:",
            response["usage"]["completion_tokens"],
            "total_token_used:",
            response["usage"]["total_tokens"],
        )
        return result

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        stop=tenacity.stop_after_attempt(5),
        reraise=True,
    )
    def chat_method(self, text, method_prompt_token=800):
        
        text_token = len(self.encoding.encode(text))
        clip_text_index = int(
            len(text) * (self.max_token_num - method_prompt_token) / text_token
        )
        clip_text = text[:clip_text_index]
        messages = [
            {
                "role": "system",
                "content": "You are a researcher in the field of ["
                + self.key_word
                + "] who is good at summarizing papers using concise statements",
            },
            # chatgpt 角色
            {
                "role": "assistant",
                "content": "This is the <summary> and <Method> part of an English document, where <summary> you have summarized, but the <Methods> part, I need your help to read and summarize the following questions."
                + clip_text,
            },
            # 背景知识
            {
                "role": "user",
                "content": """                 
                 6. Describe in detail the methodological idea of this article. Be sure to use {} answers (proper nouns need to be marked in English). For example, its steps are.
                    - (1):...
                    - (2):...
                    - (3):...
                 Follow the format of the output that follows: 
                 6. Methods: \n\n
                    - (1):xxx;\n 
                    - (2):xxx;\n 
                    - (3):xxx;\n  
                 Be sure to use {} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, if not, you can not write.
                 """.format(
                    self.language, self.language
                ),
            },
        ]
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        """
        response = self.llm.create_chat_completion(
        messages=messages,
        max_tokens=1000,
        stream=False
        )
        result = ""
        for choice in response["choices"]:
            result += choice["message"]["content"]
        #print("method_result:\n", result)
        print(
            "prompt_token_used:",
            response["usage"]["prompt_tokens"],
            "completion_token_used:",
            response["usage"]["completion_tokens"],
            "total_token_used:",
            response["usage"]["total_tokens"],
        )
        return result

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
        stop=tenacity.stop_after_attempt(5),
        reraise=True,
    )
    def chat_summary(self, text, summary_prompt_token=1100):
        text_token = len(self.encoding.encode(text))
        clip_text_index = int(
            len(text) * (self.max_token_num - summary_prompt_token) / text_token
        )
        clip_text = text[:clip_text_index]
        messages = [
            {
                "role": "system",
                "content": "You are a researcher in the field of ["
                + self.key_word
                + "] who is good at summarizing papers using concise statements",
            },
            {
                "role": "assistant",
                "content": "This is the title, author, link, abstract and introduction of an English document. I need your help to read and summarize the following questions: "
                + clip_text,
            },
            {
                "role": "user",
                "content": """                 
                 1. list all the authors' names (use English)
                 2. mark the first author's affiliation (output {} translation only)                 
                 3. mark the keywords of this article (use English)
                 4. link to the paper, Github code link (if available, fill in Github:None if not)
                 5. summarize according to the following four points.Be sure to use {} answers (proper nouns need to be marked in English)
                    - (1):What is the research background of this article?
                    - (2):What are the past methods? What are the problems with them? Is the approach well motivated?
                    - (3):What is the research methodology proposed in this paper?
                    - (4):On what task and what performance is achieved by the methods in this paper? Can the performance support their goals?
                 Follow the format of the output that follows:                  
                 1. Authors: xxx\n\n
                 2. Affiliation: xxx\n\n                 
                 3. Keywords: xxx\n\n   
                 4. Urls: xxx or xxx , xxx \n\n      
                 5. Summary: \n\n
                    - (1):xxx;\n 
                    - (2):xxx;\n 
                    - (3):xxx;\n  
                    - (4):xxx.\n\n     
                 Be sure to use {} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not have too much repetitive information, numerical values using the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed.         
                 """.format(
                    self.language, self.language, self.language
                ),
            },
        ]
        openai.base_url = "https://free.gpt.ge/v1/"
        openai.default_headers = {"x-foo": "true"}
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        """
        response = self.llm.create_chat_completion(
        messages=messages,
        max_tokens=1000,
        stream=False
        )
        result = ""
        for choice in response["choices"]:
            result += choice["message"]["content"]
        #print("method_result:\n", result)
        #result = self.translate_text(result)
        print(
            "prompt_token_used:",
            response["usage"]["prompt_tokens"],
            "completion_token_used:",
            response["usage"]["completion_tokens"],
            "total_token_used:",
            response["usage"]["total_tokens"],
        )
        return result

    def export_to_markdown(self, text, file_name, mode="w"):
        # 打开一个文件，以写入模式
        with open(file_name, mode, encoding="utf-8") as f:
            # 将html格式的内容写入文件
            f.write(text)

    # 定义一个方法，打印出读者信息
    def show_info(self):
        print(f"Key word: {self.key_word}")
        print(f"Query: {self.query}")
        print(f"Sort: {self.sort}")
    
    def translate_text(self, text):
        prompt = "Titles, keywords and proper nouns should in english, statements as concise and academic as possibleplease translate the following English to Chinese:"+text
        response = self.llm.create_chat_completion(
        messages=[{
            "role": "user",
            "content": prompt
        }],
        max_tokens=1000,
        stream=False
    )

        result = ""
        for choice in response["choices"]:
            result += choice["message"]["content"]
            
        return result

def chat_arxiv_main(args, texts):
    reader1 = Reader(args.query, args.key_word,args=args)
    reader1.show_info()
    paper_list = reader1.get_arxiv_web(
       texts
    )
    result = reader1.summary_with_chat(paper_list)
    return result


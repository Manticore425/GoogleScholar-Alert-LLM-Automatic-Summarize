import re
import time
def clean_summary(data):
    pattern = r"标题:\s*(.*?)\n摘要:(.*?)____________________"

# 用正则表达式提取每篇论文
    matches = re.findall(pattern, data, re.S)

    # 解析字段
    papers = []
    for match in matches:
        title, content = match
        # 提取摘要并过滤掉为 "None" 的条目
        abstract_match = re.search(r"摘要：(.*?)(6. 方法：|$)", content, re.S)
        abstract = abstract_match.group(1).strip() if abstract_match else "N/A"
        if abstract == "None" or abstract == "N/A" or len(abstract) < 5:
            continue  # 跳过没有摘要的条目

        paper = {"title": title.strip(), "abstract": abstract}

        authors_match = re.search(r"作者：(.*?)\n", content)
        paper["authors"] = authors_match.group(1).strip() if authors_match else "N/A"

        keywords_match = re.search(r"关键词：(.*?)\n", content)
        paper["keywords"] = keywords_match.group(1).strip() if keywords_match else "N/A"

        link_match = re.search(r"链接：(https?://[^\s，,：]+)", content)
        paper["link"] = link_match.group(1).strip() if link_match else "N/A"

        github_match = re.search(r"Github:\s*(https?://[^\s]+)", content)
        paper["github"] = github_match.group(1).strip() if github_match else "N/A"

        method_match = re.search(r"6\. 方法[:：](.*?)(7\. 结论|$)", content, re.S)
        paper["method"] = method_match.group(1).strip() if method_match else "N/A"

        conclusion_match = re.search(r"7. 结论：(.*?)$", content, re.S)
        paper["conclusion"] = conclusion_match.group(1).strip() if conclusion_match else "N/A"

        papers.append(paper)
    return papers 

def convert_html(papers):
        
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>论文列表</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 20px;
                background-color: #f4f4f9;
            }
            .paper {
                background: #ffffff;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .paper h2 {
                margin-top: 0;
            }
            .paper a {
                color: #007BFF;
                text-decoration: none;
            }
            .paper a:hover {
                text-decoration: underline;
            }
            .keywords {
                font-style: italic;
                color: #555;
            }
        </style>
    </head>
    <body>
        <h1>论文列表</h1>
    """

    # 遍历每篇论文添加到 HTML
    for paper in papers:
        html_content += f"""
        <div class="paper">
            <h2>{paper['title']}</h2>
            <p><strong>作者:</strong> {paper['authors']}</p>
            <p><strong>关键词:</strong> <span class="keywords">{paper['keywords']}</span></p>
            <p><strong>摘要:</strong> {paper['abstract']}</p>
            <p><strong>链接:</strong> <a href="{paper['link']}" target="_blank">{paper['link']}</a></p>
            <p><strong>Github:</strong> <a href="{paper['github']}" target="_blank">{paper['github']}</a></p>
            <p><strong>方法:</strong> {paper['method']}</p>
            <p><strong>结论:</strong> {paper['conclusion']}</p>
            
        </div>
        """

    # 添加 HTML 结束标签
    html_content += """
    </body>
    </html>
    """

    # 保存为HTML文件
    output_path = "./papers_list_{}.html".format(time.strftime("%Y%m%d%H%M%S"))
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)
    
    return output_path
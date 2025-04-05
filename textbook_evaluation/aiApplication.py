# -*- coding: utf-8 -*-
import datetime
import json
import os
import re
import time

import requests
from openai import OpenAI
from enum import Enum
from baseData import BookReview
import fitz


# 评价类型枚举
class EVAL_TYPE(Enum):
    TOTAL = 0
    SUITABILITY = 1  # 适宜性
    POLITICAL = 2  # 政治性
    SCIENTIFIC = 3  # 科学性
    IDEOLOGICAL = 4  # 思想性


# 定义一个映射字典，将评价类型映射到对应的属性名
EVAL_TYPE_MAPPING = {
    EVAL_TYPE.TOTAL: ('overall_review', 'overall_score'),
    EVAL_TYPE.POLITICAL: ('political_review', 'political_score'),
    EVAL_TYPE.IDEOLOGICAL: ('ideological_review', 'ideological_score'),
    EVAL_TYPE.SCIENTIFIC: ('scientific_review', 'scientific_score'),
    EVAL_TYPE.SUITABILITY: ('applicability_review', 'applicability_score'),
}




# 基础调用 LLM模型方法
def openai(user_prompt, system_prompt=None, temperature=0.1):
    try:
        client = OpenAI(api_key=LLM_KEY, base_url=LLM_URL, max_retries=1)
        if system_prompt:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    }, {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
                model=LLM_Model,
                temperature=temperature,
            )
        else:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
                model=LLM_Model,
                temperature=0.1,
            )
        #     休眠1.5s
        time.sleep(1.5)
        return response.choices[0].message.content
    except Exception as e:
        print(e)
        return ""


# 评价-> 适宜性
# textbook 教材实体类 split_result 教材分片
def evaluate_about_suitability(textbook, split_result):
    sys_prompt = """你是一位资深的学院教授，对 {name} 这本教材相关领域有多年的教学经验，这里会给出这本教材的节选内容，请帮忙评价一下这本教材是否适合备课且易于学生自习。
教材的的节选内容：
{text}"""
    user_prompt = "请输出结论和分析，并按照100分满分制进行打分"
    total_user_prompt = "必须严格按照要求的格式输出，不要输出额外的东西，只输出评分和评价。下面是其他几位教授的评价：{evals_str}"
    total_sys_prompt = """你是一位资深的学院教授，对 {name} 这本教材相关领域有多年的教学经验，用户会给你其他几位教授根据收到的教材节选部分进行的评价和打分，请输出汇总结论和分析，并按照100分满分制进行打分。
注意：只给出你最终的评分和评价，并按照以下格式输出结果，不要输出额外的东西，只输出评分和评价：
评分：
评价：
-------------------------

举例：
评分：85
评价：这本教材讲述了......
这本教材在相关领域教学使用中......
这本教材在自习情况下......
                """
    return common_evaluate(textbook, split_result, user_prompt, sys_prompt, total_user_prompt, total_sys_prompt,
                           EVAL_TYPE.SUITABILITY)


# 评价-> 政治性
def evaluate_about_political(textbook, split_result):
    sys_prompt = """你是一位资深的学院教授，对 {name} 这本教材相关领域有多年的教学经验，这里会给出这本教材的节选内容，请帮忙评价一下这本教材的政治正确性，要分别从培“养学生的家国情怀，将爱国主义有机融于教材体系；无诋毁我国形象的反面案例、文字或图片等；增强学生对中华民族的情感认同，不断铸牢中华民族共同体意识’体现中国优秀传统文化，提升学生的文化认同具有正确的政治立场与价值观，坚定中国特色社会主义道路自信”方面进行评价，
教材的的节选内容：
{text}"""
    user_prompt = '''请输出结论和分析，并按照100分满分制进行打分，注意评价的方面是“养学生的家国情怀，将爱国主义有机融于教材体系；无诋毁我国形象的反面案例、文字或图片等；增强学生对中华民族的情感认同，不断铸牢中华民族共同体意识’体现中国优秀传统文化，提升学生的文化认同具有正确的政治立场与价值观，坚定中国特色社会主义道路自信”，不是评价具体内容'''
    total_user_prompt = '必须严格按照要求的格式输出，不要输出额外的东西，只输出评分和评价，注意，这是关于教材的政治性评价。下面是其他几位教授的评价：{evals_str}'
    total_sys_prompt = """你是一位学院的资深教导主任，对 {name} 这本教材相关领域有多年的教学经验，对教材的政治正确性有着充分的了解，会针对国家认同、民族认同、文化认同、道路认同不同方面有明确正向的态度，下面你将要评价这本教材的政治性并给出评价和评分。用户会给你几位其他教授根据收到的教材节选部分进行的政治性评价和打分，请输出汇总结论和分析，并按照100分满分制进行打分，并且，打分不能低于80分。
注意：只给出你最终关于这本教材的政治性评分和评价，并按照以下格式输出结果，不要输出额外的东西，只输出评分和评价：
评分：
评价：

-------------------------

举例：
评分：95
评价：这本教材的政治性评价如下：....
                """
    return common_evaluate(textbook, split_result, user_prompt, sys_prompt, total_user_prompt, total_sys_prompt,
                           EVAL_TYPE.POLITICAL)


# 评价-> 科学性
def evaluate_about_scientific(textbook, split_result):
    sys_prompt = """你是一位资深的学院教授，对 {name} 这本教材相关领域有多年的教学经验，这里会给出这本教材的节选内容，请从“全面性、系统性、规范性”评价这本教材的科学性，其中的“全面性”是该教材的经典知识与理论覆盖的全面性；“系统性”是指该教材内容知识体系的连贯性与系统性，节选段落无拼凑感；“规范性”主要指语言流畅通俗易懂
教材的的节选内容：
{text}"""
    user_prompt = '''请输出结论和分析，并按照100分满分制进行打分'''
    total_user_prompt = '必须严格按照要求的格式输出，不要输出额外的东西，只输出评分和评价，注意，这是关于教材的科学性评价。下面是其他几位教授的评价：{evals_str}'
    total_sys_prompt = """你是一位学院的资深教授，对 {name} 这本教材相关领域有多年的教学经验，对教材的科学性有着充分的了解，比如“全面性”是该教材的经典知识与理论覆盖的全面性；“系统性”是指该教材内容知识体系的连贯性与系统性，节选段落无拼凑感；“规范性”主要指语言流畅通俗易懂。下面你将要评价这本教材的科学性并给出评价和评分。用户会给你几位其他教授根据收到的教材节选部分进行的科学性评价和打分，请输出汇总结论和分析，并按照100分满分制进行打分。
注意：只给出你最终关于这本教材的科学性评分和评价，并按照以下格式输出结果，不要输出额外的东西，只输出评分和评价：
评分：
评价：

-------------------------

举例：
评分：95
评价：这本教材的科学性评价如下：....
                """
    return common_evaluate(textbook, split_result, user_prompt, sys_prompt, total_user_prompt, total_sys_prompt,
                           EVAL_TYPE.SCIENTIFIC)


# 评价-> 思想性
def evaluate_about_ideological(textbook, split_result, base_path):
    sys_prompt = "今年是" + str(datetime.datetime.now().year) + """，你是一位资深的学院教授，对 {name} 这本教材相关领域有多年的教学经验，这里会给出这本教材的节选内容，请从“内容前瞻性和思想启迪性”评价这本教材的思想性，具体来说就是要评价该教材是否反映前沿理论观点、是否反映最新实践成果、近5年参考文献比例是否较多、是否能启迪学生的科学思维，形成思想碰撞
教材的的节选内容：
{text}"""
    user_prompt = '''请输出结论和分析，并按照100分满分制进行打分'''
    references = ''
    if os.path.exists(base_path + '/references.txt'):
        with open(base_path + '/references.txt', 'r', encoding='utf-8') as f:
            references = f'''
    该教材的引用内容是：
    {f.read()}    
    '''
    total_user_prompt = "今年是" + str(
        datetime.datetime.now().year) + '。必须严格按照要求的格式输出，不要输出额外的东西，只输出评分和评价，注意，这是关于教材的思想性评价。下面是其他几位教授的评价：{evals_str}' + references
    total_sys_prompt = """你是一位学院的资深教授，对 {name} 这本教材相关领域有多年的教学经验，对教材的思想性有着充分的了解，思想性主要是指“内容前瞻性和思想启迪性”，具体来说就是要评价该教材是否反映前沿理论观点、是否反映最新实践成果、近5年参考文献比例是否较多、是否能启迪学生的科学思维，形成思想碰撞。用户会给你几位其他教授根据收到的教材节选部分进行的科学性评价和打分，请输出汇总结论和分析，并按照100分满分制进行打分。
注意：只给出你最终关于这本教材的思想性评分和评价，并按照以下格式输出结果，不要输出额外的东西，只输出评分和评价：
评分：
评价：

-------------------------

举例：
评分：95
评价：这本教材的思想性评价如下：....
                """
    return common_evaluate(textbook, split_result, user_prompt, sys_prompt, total_user_prompt, total_sys_prompt,
                           EVAL_TYPE.IDEOLOGICAL)


# 评价-> 总体
def evaluate_total(textbook):
    four_remark = f"""
    政治性评分: {textbook.political_score} 
    政治性评价: {textbook.political_review} 

    思想性评分: {textbook.ideological_score}
    思想性评价: {textbook.ideological_review} 

    科学性评分: {textbook.scientific_score}
    科学性评价: {textbook.scientific_review} 

    适用性评分: {textbook.applicability_score}
    适用性评价: {textbook.applicability_review}
    """
    sys_prompt = f"""你是一位学院的资深教授，对 {textbook.book_title} 这本教材相关领域有多年的教学经验，现在用户将会提供关于这本教材的一些评价，请你根据这些评价给出总评，并给出100字左右的总评价"""
    user_prompt = f"该教材的评价：{four_remark}"
    result = openai(user_prompt, sys_prompt)
    if not result:
        raise Exception("没有评价结果")
    textbook.overall_review = result
    four_score = textbook.political_score + textbook.ideological_score + textbook.scientific_score + textbook.applicability_score
    total_num = 4
    total_score = round(four_score / total_num)
    textbook.overall_score = total_score
    return textbook


def common_evaluate(textbook, split_result, the_user_prompt, the_sys_prompt, total_user_prompt, total_sys_prompt,
                    eval_type, can_retry=0):
    if can_retry >= 5:
        raise Exception("评价异常，重试次数已达上限")

    # 逐段进行评价
    evals = []
    for text in split_result:
        print("本次输入片段为 -> " + str(len(text)))
        try:
            onece = openai(the_user_prompt, the_sys_prompt.format(name=textbook.book_title, text=text), 0.3)
            evals.append(onece)
        except Exception as e:
            print(f"重试评价>>>{e}")
            continue

    if not evals:
        raise Exception("没有评价结果")


    # 对于所有的教授评价进行汇总评价
    batch_size = 30  # 每次处理 5 条评价
    aggregated_evaluations = []

    for i in range(0, len(evals), batch_size):
        batch_evals = evals[i:i + batch_size]
        batch_evals_str = "\n".join(f"教授{j + 1}评价：{e}" for j, e in enumerate(batch_evals))
        print("[评价总结1-->] 长度 -> " + str(len(batch_evals_str)))
        # 对每批次进行汇总
        batch_summary = openai(
            total_user_prompt.format(evals_str=batch_evals_str),
            total_sys_prompt.format(name=textbook.book_title)
        )
        aggregated_evaluations.append(batch_summary)

    # 最终汇总所有批次的结果
    final_evals_str = "\n".join(aggregated_evaluations)
    print("[最总评价总结2->] 长度 -> " + str(len(final_evals_str)))
    evaluation = openai(
        total_user_prompt.format(evals_str=final_evals_str),
        total_sys_prompt.format(name=textbook.book_title)
    )

    if not evaluation:
        raise Exception("没有评价结果")

    # 处理评价文本
    evaluation = _rearrange_evaluation(evaluation)

    try:
        score = 80  # 默认评分
        remark = evaluation

        for line in evaluation.split("\n"):
            if line.startswith("评分："):
                score = int(line.replace("评分：", "").strip())
                remark = evaluation.replace(line, "").strip()
                break  # 找到评分后，提前退出循环

        print("评分:" + str(score) + "完成一项评价-->" + str(eval_type) + "-->" + remark)

        # 获取对应的属性名
        if eval_type in EVAL_TYPE_MAPPING:
            review_attr, score_attr = EVAL_TYPE_MAPPING[eval_type]
            setattr(textbook, review_attr, remark)
            setattr(textbook, score_attr, score)
        else:
            raise Exception("未知的评价类型")
    except Exception as e:
        print(f"重试评价>>>{e}")
        return common_evaluate(textbook, split_result, the_user_prompt, the_sys_prompt,
                               total_user_prompt, total_sys_prompt, eval_type, can_retry + 1)
    return textbook


# 格式化评价
def _rearrange_evaluation(evaluation):
    user_prompt = f'''请把最下面的原始评价按照一个教授提交正式报告的口吻进行改写，并严格按照以下格式重新排列。注意输出时评分只输出整数数字；评价必须是纯文本格式，不得有markdown或其他任何格式出现。只输出一个最终的评分和评价，要求的输出格式是：
评分：XX
评价：YYYY


--------------------------
举例：
评分：80
评价：这本教材讲述了......
这本教材在相关领域教学使用中......
这本教材在自习情况下......
--------------------------
原始评价:
{evaluation}
'''
    return openai(user_prompt)


# 定义缩放矩阵（可动态调整缩放比例）
def get_matrix(scale_factor):
    """
    根据缩放因子生成 Matrix 对象。
    :param scale_factor: 缩放比例 (例如 2 表示放大两倍)
    :return: fitz.Matrix 对象
    """
    return fitz.Matrix(scale_factor, 0, 0, scale_factor, 0, 0)


# 使用 ocr 进行识别
def ocr(local_path):
    """
    调用 OCR 服务识别图片中的文字。
    :param local_path: 图片文件的本地路径
    :return: OCR 识别结果（JSON 格式），或空字典表示失败
    """
    # 检查文件是否存在
    if not os.path.exists(local_path):
        print(f"文件不存在: {local_path}")
        return {}

    # 检查文件是否为图片（简单验证扩展名）
    valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    _, ext = os.path.splitext(local_path)
    if ext.lower() not in valid_extensions:
        print(f"不支持的文件格式: {ext}")
        return {}

    try:
        # 打开文件并发送请求
        with open(local_path, 'rb') as f:
            files = {'file': (os.path.basename(local_path), f)}
            response = requests.post(OCR_URL, files=files)

        # 检查响应状态码
        if response.status_code == 200:
            result = response.json()
            # print("OCR 成功:", result)
            return result
        else:
            print(f"OCR 请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
            return {}
    except requests.RequestException as e:
        print(f"网络请求失败: {e}")
        return {}
    except ValueError as e:
        print(f"解析响应失败: {e}")
        return {}


# llm 排版
def organize_text(pre_page_text, page_text):
    if LLM_OPEN_OPTIMAIZE_TEXT:
        # 整理下当前页的内容
        if len(pre_page_text) > 0:
            pre_page_text = f'''
    这里是用户输入页面的上一页的内容：        
    {pre_page_text}
    '''
        sys_prompt = f"你是一位出版社的优秀专家，善于排版和编辑文本，用户会输入某本书其中一页的内容的markdown格式，{pre_page_text}由于输入的内容是OCR的结果，可能存在排版不对和内容识别错误情况，请纠正其中可能出现的OCR错误字词，并将整个文本以更好的格式输出，不要改变原意，只要最后输出结果，不要解释，不要说明，不要处理思路。"
        user_prompt = page_text
        return openai(user_prompt, sys_prompt)
    else:
        return None


# 书籍拆分
def split_textbook(base_dir, SPLIT_TOKEN_NUM):
    result = []
    try:
        with open(base_dir + 'all.md', 'r', encoding='utf-8') as f:
            all_text = f.read()

        # 按句子分割（保留标点符号）
        parts = re.split(r'([。！？])', all_text)
        sentences = [parts[i] + parts[i + 1] for i in range(0, len(parts) - 1, 2)]
        if len(parts) % 2 == 1:
            sentences.append(parts[-1])  # 添加最后一个无标点的部分

        current_segment = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(sentence) > SPLIT_TOKEN_NUM:
                # 当前句子超过限制，需先将已有段落加入
                if current_segment:
                    result.append(current_segment.strip())
                    current_segment = ""

                # 直接将长句切分为多个小块
                for i in range(0, len(sentence), SPLIT_TOKEN_NUM):
                    result.append(sentence[i:i + SPLIT_TOKEN_NUM].strip())
            else:
                if len(current_segment) + len(sentence) > SPLIT_TOKEN_NUM:
                    result.append(current_segment.strip())
                    current_segment = sentence
                else:
                    current_segment += sentence

        if current_segment:
            result.append(current_segment.strip())

    except Exception as e:
        print(f"Error occurred: {e}")
        return []

    return result


# 提取书籍基础信息
def _fetch_textbook_info(textbook, base_dir, can_retry=True):
    text = _conbine_page_content(base_dir, 0, 6)
    sys_prompt = """你是一位出版社的优秀专家，用户会给出某本书前几页内容（包括封面页）的markdown格式，请帮忙从中提取书名、isbn、作者、出版年月的信息。只输出最后结果，不要解释，不要说明，不要处理思路，不要总结文本，你的唯一任务就是提取下面的信息，而且要用txt格式输出。
请认真阅读用户给的文本后，必须严格按照以下格式输出提取的文字：
<data>
书名: xxx
isbn: xxx
作者: xxx
出版年月: xxx
出版商: xxx
版本: xxx
</data>
"""
    user_prompt = f'''请帮我从书前7页的文字中提取书名、isbn、作者、出版年月等信息，按照以下格式输出：
<data>
书名: xxx
isbn: xxx
作者: xxx
出版年月: xxx
出版商: xxx
版本: xxx
</data>
这本书的文字是：
{text}'''
    if len(user_prompt) > 3000:
        user_prompt = user_prompt[:3000]
    result = openai(user_prompt, sys_prompt)
    try:
        items = result.split("\n")
        for item in items:
            if item.startswith("书名:"):
                textbook.book_title = item.replace("书名:", "").strip()
                if '《' in textbook.book_title:
                    textbook.book_title = textbook.book_title.replace('《', '')
                if '》' in textbook.book_title:
                    textbook.book_title = textbook.book_title.replace('》', '')
            elif item.startswith("isbn:"):
                textbook.isbn = item.replace("isbn:", "").strip()
            elif item.startswith("作者:"):
                textbook.author = item.replace("作者:", "").strip()
            elif item.startswith("出版年月:"):
                textbook.publish_date = item.replace("出版年月:", "").strip()
            elif item.startswith("出版商:"):
                textbook.publish_date = item.replace("出版商:", "").strip()
            elif item.startswith("版本:"):
                textbook.edition = item.replace("版本:", "").strip()
    except Exception as e:
        if can_retry:
            _fetch_textbook_info(textbook, base_dir, False)
    return textbook


# 提取目录信息
def _extract_table_of_contents(textbook, base_dir, page_size):
    end_page = 30
    if page_size < 30:
        end_page = page_size
    text = _conbine_page_content(base_dir, 0, end_page)
    sys_prompt = f"""你是一位出版社的优秀专家，这里最后会给出某本书前几页内容（包括封面页）的markdown格式，请帮忙从中提取目录。
    只输出最后结果，不要解释，不要说明，不要处理思路。
    书的内容：   
    {text}
    """
    user_prompt = '''请直接输出目录，不要额外内容'''
    textbook.directory = openai(user_prompt, sys_prompt)
    return textbook


# 获取引用信息
def _extract_references(base_dir, page_size):
    start_page = page_size - 30
    if start_page < 0:
        start_page = 0
    text = _conbine_page_content(base_dir, start_page, page_size - 1)
    sys_prompt = f"""你是一位出版社的优秀专家，这里最后会给出某本书最后几页内容的markdown格式，请帮忙从中提取该书的引用参考部分内容。
    只输出最后结果，不要解释，不要说明，不要处理思路。
    书的内容：
    {text}
    """
    user_prompt = '''请直接输出该书的引用参考部分，不要额外内容'''
    result = openai(user_prompt, sys_prompt)
    with open(base_dir + 'references.md', 'w', encoding='utf-8') as f:
        f.write(result)


# 获取引用信息2
def _conbine_page_content(base_dir, start_page, end_page):
    result = []
    for page_no in range(start_page, end_page):
        if os.path.exists(f"{base_dir}{page_no}.md"):
            with open(f"{base_dir}{page_no}.md", 'r', encoding='utf-8') as f:
                result.append(f.read())
    return "  \n".join(result)


if __name__ == '__main__':
    # 测试流程
    book_dir = 'D:\\programWorkPlace\\PythonDemo\\textbook_evaluation\\book\\材料成型工艺基础.pdf'

    # 定义临时工作目录
    tmp_work_dir = 'D:\\programWorkPlace\\PythonDemo\\textbook_evaluation\images\\'

    # 确保临时目录存在
    os.makedirs(tmp_work_dir, exist_ok=True)

    try:
        doc = fitz.open(book_dir)
        # 获取总页数
        page_size = len(doc)

        for page_no in range(page_size):
            try:
                page = doc[page_no]

                # 动态设置缩放比例
                if page_no == 0:
                    scale_factor = 1  # 第一页使用原始大小
                else:
                    scale_factor = 2  # 其他页放大两倍

                # 获取缩放矩阵
                m = get_matrix(scale_factor)

                # 生成图片文件路径
                temp_file_image = os.path.join(tmp_work_dir, f"{page_no}.png")

                # 将页面转换为图片并保存
                pix = page.get_pixmap(matrix=m)
                pix.save(temp_file_image)

                print(f"已保存第 {page_no + 1} 页为图片: {temp_file_image}")

            except Exception as e:
                print(f"处理第 {page_no + 1} 页时出错: {e}")
                continue

        # 提取封面图片
        cover_img = '.cover.png'
        # 保存封面图...
        print(f"完成封面提取 , 进入OCR识别环节")

        per25, per50, per75 = int(page_size / 4), int(page_size / 2), int(page_size * 3 / 4)

        for page_no in range(0, page_size):
            if page_no == per25:
                print(f"完成25% OCR识别")
            elif page_no == per50:
                print(f"完成50% OCR识别")
            elif page_no == per75:
                print(f"完成75% OCR识别")
            page_ocr_result_file = f"{tmp_work_dir}{page_no}.json"
            if os.path.exists(page_ocr_result_file):
                continue
            page_ocr_result = json.dumps(ocr(f"{tmp_work_dir}{page_no}.png"))
            with open(page_ocr_result_file, 'w', encoding='utf-8') as f:
                f.write(page_ocr_result)
        # 进入文本整理环节
        # 每一页给llm整理下当前页的内容
        pre_page_text = ''
        all_text = []
        print("进入文本整理")
        for page_no in range(0, page_size):
            if page_no == per25:
                print(f"完成25% 文本整理")
            elif page_no == per50:
                print(f"完成55% 文本整理")
            elif page_no == per75:
                print(f"完成75% 文本整理")
            try:
                with open(f"{tmp_work_dir}{page_no}.json", 'r', encoding='utf-8') as f:
                    result_json = json.load(f)
                    markdown = []
                    page_text = ''
                    if os.path.exists(f"{tmp_work_dir}{page_no}.md"):
                        with open(f"{tmp_work_dir}{page_no}.md", 'r', encoding='utf-8') as ff:
                            page_text = ff.read()
                            all_text.append(page_text)
                            pre_page_text = page_text
                        continue
                    for elem in result_json['response']:
                        if 'res' in elem and (elem['res'] == {} or elem['res'] == []):
                            continue
                        type = elem['type']
                        if type in ['title', 'text', 'reference', 'table_caption', 'figure_caption', 'figure',
                                    'equation']:
                            tmp = []
                            for res in elem['res']:
                                if 'text' in res:
                                    tmp.append(res['text'])
                            if len(tmp) > 0:
                                markdown.append(''.join(tmp))
                        elif type == 'table':
                            if 'html' in elem['res']:
                                markdown.append(elem['res']['html'])
                        else:
                            if type not in ['header', 'footer']:
                                print(f"未知类型: {type}")
                        if len(markdown) > 0:
                            page_text = "  \n".join(markdown)
                            tmp_text = organize_text(pre_page_text, page_text)
                            if tmp_text and len(tmp_text) > 0:
                                page_text = tmp_text
                            with open(f"{tmp_work_dir}{page_no}.md", 'w', encoding='utf-8') as f:
                                f.write(page_text)
                            all_text.append(page_text)
                    pre_page_text = page_text
            except Exception as e:
                pre_page_text = ''
                print(f"处理第 {page_no + 1} 页时出错: {e}")
        print("完成文本整理")

        textbook_bean = BookReview()
        # 提取基本信息
        textbook_bean = _fetch_textbook_info(textbook_bean, tmp_work_dir)
        print("完成基本信息提取")
        # 提取目录信息
        textbook_bean = _extract_table_of_contents(textbook_bean, tmp_work_dir, page_size)
        print("完成目录提取")
        # 引用提取
        _extract_references(tmp_work_dir, page_size)
        print("完成引用提取")

        all_content = re.sub(r"[\s\n]+", " ", "  \n".join(all_text))
        all_content_md = f"{tmp_work_dir}all.md"
        with open(all_content_md, 'w', encoding='utf-8') as f:
            f.write(all_content)

        split_result = split_textbook(tmp_work_dir, SPLIT_TOKEN_NUM)

        print(textbook_bean.book_title)
        #   进入评价页面
        textbook_bean2 = evaluate_about_suitability(textbook_bean, split_result)
        print("完成了 适用性评价")
        textbook_bean3 = evaluate_about_political(textbook_bean2, split_result)
        print("完成了 政治性评价")
        textbook_bean4 = evaluate_about_scientific(textbook_bean3, split_result)
        print("完成了 科学性评价")
        textbook_bean5 = evaluate_about_ideological(textbook_bean4, split_result, tmp_work_dir)
        print("完成了 思想性评价")
        # 进入总评
        textbook_bean6 = evaluate_total(textbook_bean5)
        print("完成了 总评")
        print(f"总评分:" + str(textbook_bean6.overall_score) + "总评价:" + textbook_bean6.overall_review + \
              "适用性评分:" + str(
            textbook_bean6.applicability_score) + "适用性评价:" + textbook_bean6.applicability_review + \
              "科学性评分:" + str(textbook_bean6.scientific_score) + "科学性评价:" + textbook_bean6.scientific_review + \
              "思想性评分:" + str(textbook_bean6.ideological_score) + "思想性评价:" + textbook_bean6.ideological_review)
    except Exception as e:
        print(f"处理文件时出错: {e}")

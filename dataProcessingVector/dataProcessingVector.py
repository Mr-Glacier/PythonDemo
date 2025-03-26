from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import time

import requests
import json
from tqdm import tqdm
import pandas as pd
import os
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

app = Flask(__name__)
# 设置密钥
app.secret_key = 'YuoMNhZKgHsCu45XnEViPmEWcFZMdFTdp5ezZ6'
# 内置账户
USERS = {
    "admin": "password"
}

# 配置文件上传目录
# 主要存储上传的文件
main_path = os.getenv('WORKSPACE', 'D:\programWorkPlace\PythonDemo\dataProcessingVector\workspace')
# 临时处理的目录
temp_path = os.getenv('TEMP_PATH', 'D:\programWorkPlace\PythonDemo\dataProcessingVector\workspace')
# Qdrant 服务器地址
client_url = os.getenv('QDRANT_URL', '192.168.0.253')
# text2text 服务地址
text2vec_url = os.getenv('TEXT2VEC_URL', '192.168.0.253')

client = QdrantClient(client_url, port=6333, timeout=3600)


# 前端页面路由
@app.route('/')
def index():
    return render_template('login.html')  # 渲染前端页面


# 业务页面路由
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    return render_template('dashboard.html')


# 登出 返回首页
@app.route('/logout')
def logout():
    session.clear()  # 清空会话
    return redirect(url_for('index'))  # 使用视图函数名


# 登录接口
@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "用户名和密码不能为空"}), 400

    # 验证用户名和密码
    if username in USERS and USERS[username] == password:
        session['logged_in'] = username
        return jsonify({"message": "登录成功"}), 200
    else:
        return jsonify({"message": "用户名或密码错误"}), 401


# 业务接口1: 上传 .csv文件
@app.route('/api/upload', methods=['POST'])
def upload_file():
    # 检查是否登录
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    # 检查是否有文件在请求中
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    # 如果用户没有选择文件，浏览器可能会提交一个空的文件名
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 检查文件格式是否合法,不合法直接返回
    ALLOWED_EXTENSIONS = {'csv'}
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'File format not allowed. Only .csv files are accepted'}), 400

    # 文件保存（可根据需要修改保存路径）
    try:
        file.save(os.path.join(main_path, file.filename))
        return jsonify({'message': 'File uploaded successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500


# 业务接口2: 获取 .csv文件列表
@app.route('/api/list_csv', methods=['GET'])
def list_csv():
    # 确保上传目录存在
    if not os.path.exists(main_path):
        return jsonify({'error': 'Upload folder does not exist'}), 404

    try:
        # 获取所有 .csv 文件及其最后修改时间
        csv_files_with_time = []
        for f in os.listdir(main_path):
            file_path = os.path.join(main_path, f)
            if f.endswith('.csv') and os.path.isfile(file_path):  # 确保是文件且扩展名为 .csv
                modification_time = os.path.getmtime(file_path)  # 获取最后修改时间
                csv_files_with_time.append({
                    'filename': f,
                    'upload_time': modification_time
                })

        # 按上传时间排序（从旧到新）
        csv_files_with_time.sort(key=lambda x: x['upload_time'])

        # 格式化时间为可读格式（可选）
        from datetime import datetime
        formatted_files = [
            {
                'filename': item['filename'],
                'upload_time': datetime.fromtimestamp(item['upload_time']).strftime('%Y-%m-%d %H:%M:%S')
            }
            for item in csv_files_with_time
        ]

        return jsonify({'csv_files': formatted_files}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500


# 业务接口3: 删除 .csv文件
@app.route('/api/delete_csv', methods=['DELETE'])
def delete_file():
    """
    删除指定文件的接口。
    请求方法：DELETE
    参数：filename（文件名）
    返回：JSON 格式的响应
    """
    # 获取请求中的文件名参数
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': '缺少文件名参数'}), 400

    # 构建文件路径
    file_path = os.path.join(main_path, filename)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return jsonify({'error': f'文件 {filename} 不存在'}), 404

    try:
        # 删除文件
        os.remove(file_path)
        return jsonify({'message': f'文件 {filename} 已成功删除'}), 200
    except Exception as e:
        # 捕获异常并返回错误信息
        return jsonify({'error': f'删除文件失败：{str(e)}'}), 500


# 业务接口4 : 处理csv 数据
@app.route('/api/process', methods=['GET'])
def process_file():
    """
    处理 CSV 文件的接口。
    参数：
        - filename: 要处理的文件名
    返回：
        - 成功时返回解析后的 CSV 数据（JSON 格式）
        - 失败时返回错误信息
    """
    # 是否登录
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    # 获取文件名参数
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': '缺少文件名参数'}), 400

    # 构建文件路径
    file_path = os.path.join(main_path, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': f'文件 {filename} 不存在'}), 404

    try:
        print("开始进行文件处理")
        start_time = time.time()
        print(file_path)
        # 清洗数据
        cleand_article_list = clean_work_data(file_path)
        # 存储向量数据
        upsert_articles(cleand_article_list)
        # 记录总耗时
        end_time = time.time()
        print(f"Total time taken: {end_time - start_time:.2f} seconds")
        time_consuming = f"本次共耗时 : {end_time - start_time:.2f} 秒"
        return jsonify({'result': '文件处理成功', 'time_consuming': time_consuming}), 200
    except Exception as e:
        # 捕获异常并返回错误信息
        return jsonify({'error': f'处理文件失败：{str(e)}'}), 500

# 核心-清洗数据-1
def clean_work_data(csv_path):
    # 数据加载
    data = pd.read_csv(csv_path, header=0, low_memory=False)
    data.isnull().sum()
    data = data.dropna()
    filter_cols = ['摘要', '关键词', '文章标题', '期刊名']
    for col in filter_cols:
        data = data[data[col] != '-']
    clean_data = data[['期刊名', '文章标题', '年', '卷', '期', '文章URL', '摘要', '关键词', '作者_JSON']]
    # 只保留有邮箱的作者
    origin_authors = {}
    for i, row in tqdm(clean_data.iterrows()):
        try:
            journal_name = row['期刊名']
            article_name = row['文章标题']
            publish_year = row['年']
            publish_vol = row['卷']
            publish_issue = row['期']
            url = row['文章URL']
            abstract_content = row['摘要']
            keyword = row['关键词']
            json_str = row['作者_JSON'].replace('\n', '')
            authors_json = json.loads(json_str)

            author_name_list = []
            author_with_email = []
            for author in authors_json:
                one_of_author = author.get('author', "unknown")
                one_of_email = author.get('mailbox', "unknown")
                one_of_institution = author.get('institution', "unknown")

                tail_email = ''
                if one_of_email != '':
                    tail_email = '(' + one_of_email + ')'
                # 打印调试信息
                author_name_list.append(one_of_author + tail_email)
                if '@' in one_of_email:
                    author_with_email.append([one_of_author, one_of_email, one_of_institution])

            for row in author_with_email:
                row_data = {
                    'author_info': {'name': row[0], 'institution': row[2]},
                    'authors': author_name_list,
                    'journal_name': journal_name,
                    'article_name': article_name,
                    'publish_year': publish_year,
                    'publish_vol': publish_vol,
                    'publish_issue': publish_issue,
                    'url': url,
                    'abstract_content': abstract_content,
                    'keyword': keyword
                }
                email = row[1]
                if origin_authors.get(email) == None:
                    origin_authors[email] = [row_data]
                else:
                    origin_authors[email].append(row_data)
        except Exception as e:
            print(e)
            continue

    # 使用时间生成文件名称
    timeTag = time.strftime("%Y%m%d%H%M%S", time.localtime())
    json_file_name = timeTag + '.json'
    with open(temp_path + json_file_name, 'w', encoding='utf-8') as f:
        json.dump(origin_authors, f, ensure_ascii=False)
    with open(temp_path + json_file_name, 'r', encoding='utf-8') as f:
        authors = json.load(f)
    article_list_deal = parse_json_data(authors)

    # 存储相关作者数据
    only_author_email_list = []
    count_only_ = 0
    for i, row in tqdm(clean_data.iterrows()):
        try:
            url = row['文章URL']
            json_str = row['作者_JSON'].replace('\n', '')
            authors_json = json.loads(json_str)

            for author in authors_json:
                one_of_author = author.get('author', "unknown")
                one_of_email = author.get('mailbox', "unknown")
                if '@' in one_of_email:
                    author_item = {'author': one_of_author, 'email': one_of_email}
                    only_author_email_list.append(author_item)
        except Exception as e:
            # print(e)
            count_only_ += 1
            continue
    with open(temp_path + timeTag + 'author_email.json', 'w', encoding='utf-8') as f:
        json.dump(only_author_email_list, f, ensure_ascii=False)
    if article_list_deal:  # 确保列表不为空
        article_list_deal.pop()
    return article_list_deal


# 核心-清洗数据-2
def parse_json_data(authors):
    article_list = []
    for email, row in authors.items():
        for row_data in row:
            author_list = row_data['authors']
            journal_name = row_data['journal_name']
            article_name = row_data['article_name']
            publish_year = row_data['publish_year']
            publish_vol = row_data['publish_vol']
            publish_issue = row_data['publish_issue']
            url = row_data['url']
            abstract_content = row_data['abstract_content']
            keyword = row_data['keyword']

            data = {'author_list': author_list,
                    'journal_name': journal_name,
                    'publish_year': publish_year,
                    'publish_vol': publish_vol,
                    'publish_issue': publish_issue,
                    'url': url,
                    'article_name': article_name,
                    'abstract_content': abstract_content,
                    'keyword': keyword
                    }
            article_list.append(data)
    return article_list


# 向量化数据 1
def upsert_articles(articles):
    article_size = len(articles)
    print('article size: ', article_size)
    prepare_articles = []
    for i in range(article_size):
        data = process_article(articles[i])
        prepare_articles.append(data)

    batch_size = 5
    for index in tqdm(range(0, article_size, batch_size)):
        data_slice = prepare_articles[index: index + batch_size]

        article_to_embs = []
        abstract_to_embs = []
        keyword_to_embs = []

        for i in data_slice:
            article_to_embs.append(i[0][0])
            abstract_to_embs.append(i[0][1])
            keyword_to_embs.append(i[0][2])

        embedding_success = False
        while not embedding_success:
            try:
                article_embs = to_embeddings(article_to_embs)
                abstract_embs = to_embeddings(abstract_to_embs)
                keyword_embs = to_embeddings(keyword_to_embs)
                embedding_success = True
            except Exception as e:
                print('embedding error: ', e)
                time.sleep(1)

        article_points = []
        abstract_points = []
        keyword_points = []

        upload_success = False
        while not upload_success:
            try:
                for cur_id, emb in enumerate(article_embs):
                    payload_data = data_slice[cur_id][1]
                    point = PointStruct(id=index + cur_id, vector=emb, payload=payload_data)
                    article_points.append(point)
                client.upsert(collection_name="paper_title", wait=False, points=article_points)

                for cur_id, emb in enumerate(abstract_embs):
                    payload_data = data_slice[cur_id][1]
                    point = PointStruct(id=index + cur_id, vector=emb, payload=payload_data)
                    abstract_points.append(point)
                client.upsert(collection_name="paper_abstract", wait=False, points=abstract_points)

                for cur_id, emb in enumerate(keyword_embs):
                    payload_data = data_slice[cur_id][1]
                    point = PointStruct(id=index + cur_id, vector=emb, payload=payload_data)
                    keyword_points.append(point)
                client.upsert(collection_name="paper_keyword", wait=False, points=keyword_points)

                upload_success = True
            except Exception as e:
                print('upload error: ', e)
                time.sleep(1)


# 向量化数据 2
def process_article(data):
    author_list = data['author_list']
    journal_name = data['journal_name']
    article_name = data['article_name']
    publish_year = data['publish_year']
    publish_vol = data['publish_vol']
    publish_issue = data['publish_issue']
    url = data['url']
    abstract_content = data['abstract_content']
    keyword = data['keyword']
    payload_data = {
        "journal_name": journal_name,
        "article_name": article_name,
        'authors': author_list,
        'publish_year': publish_year,
        'publish_vol': publish_vol,
        'publish_issue': publish_issue,
        'url': url
    }
    return [[article_name, abstract_content, keyword], payload_data]


# 向量化数据 3
def to_embeddings(text):
    return requests.post(text2vec_url, json={"qs": text}).json()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

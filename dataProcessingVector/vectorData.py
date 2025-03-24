

# 第一步清洗数据
def clean_work_data():
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
    json_file_name = timeTag+'.json'
    with open(workspace + json_file_name, 'w', encoding='utf-8') as f:
        json.dump(origin_authors, f, ensure_ascii=False)
    with open(workspace + json_file_name, 'r', encoding='utf-8') as f:
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
    with open(workspace+timeTag+'author_email.json', 'w', encoding='utf-8') as f:
        json.dump(only_author_email_list, f, ensure_ascii=False)
    if article_list_deal:  # 确保列表不为空
        article_list_deal.pop()
    return article_list_deal



def vectorize_data():
    client.delete_collection(collection_name='paper_title')
    client.delete_collection(collection_name='paper_abstract')
    client.delete_collection(collection_name='paper_keyword')

    client.create_collection(collection_name='paper_title',
                             vectors_config=VectorParams(size=768, distance=Distance.COSINE))
    client.create_collection(collection_name='paper_abstract',
                             vectors_config=VectorParams(size=768, distance=Distance.COSINE))
    client.create_collection(collection_name='paper_keyword',
                             vectors_config=VectorParams(size=768, distance=Distance.COSINE))


# 向量化调用
def to_embeddings(text):
    return requests.post(text2vec_url, json={"qs": text}).json()


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


# 处理数据方法
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
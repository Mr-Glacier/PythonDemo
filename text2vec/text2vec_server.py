from flask import Flask
from flask import request
from flask_cors import CORS
from text2vec import SentenceModel
import os
import torch

# 模型文件夹名称
model_path = os.getenv("MODEL_NAME", "text2vec-base-chinese")
# 模型文件挂载路径
base_path = '/workspaces/models/'

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
app = Flask(__name__)
CORS(app, supports_credentials=True, origins='*')

# 加载模型使用
t2v_model = SentenceModel(base_path + model_path)

# 用于检测模型是否有可用GPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'


def to_embeddings_text2vec(item):
    sentence_embeddings = t2v_model.encode(item, device=device)
    return sentence_embeddings.tolist()


def to_embeddings_text2vec_list(items):
    sentence_embeddings = t2v_model.encode(items, device=device)
    ret_list = []
    for s in sentence_embeddings:
        ret_list.append(s.tolist())
    return ret_list


@app.route('/')
def hello_world():
    return "Text2vec is running!"


@app.route('/text2vec', methods=['GET'])
def text2vec():
    return to_embeddings_text2vec(request.args.get('q'))


@app.route('/text2vec', methods=['POST'])
def text2vecs():
    data = request.json["qs"]
    return to_embeddings_text2vec_list(data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3100)

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('password.html')


@app.route('/greet', methods=['POST'])
def greet():
    name = request.form.get('name')
    return jsonify(message=f'你好, {name}!')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

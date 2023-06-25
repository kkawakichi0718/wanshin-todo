from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

import os
from werkzeug.security import generate_password_hash, check_password_hash

import datetime

app = Flask(__name__)

#環境変数の設定
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "data.sqlite")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "mysecretkey" #実査には安全な方法でキーを生成・保存する必要がある

#データベースの作成とMigrateの準備
db = SQLAlchemy(app)
Migrate(app, db)

#---------------DB定義---------------
#User テーブル
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    #外部キーリレーションシップを作る
    task = db.relationship('Task', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


#Taskテーブル
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100)) #タイトル
    status = db.Column(db.String(20))
    created_date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __init__(self, title, status, created_date, user_id):
        self.title = title
        self.status = status
        self.created_date = created_date
        self.user_id = user_id

    #Task クラスのインスタンスが表示される際に以下の形式で表示されるようにする
    def __repr__(self):
        return f'<Task {self.id}>'

@app.route("/")
def index():
    tasks = Task.query.all() #データベースからタスク一覧を取得
    return render_template("index.html", tasks = tasks)

#--------------ユーザー関係---------------
#フォームのクラスを使用
class RegistartionForm(FlaskForm):
    #フォームに提示する要素を定義
    username = StringField("ユーザー名", validators=[DataRequired()])
    password = PasswordField("パスワード", validators=[DataRequired(), EqualTo("pass_confirm")])
    pass_confirm = PasswordField("パスワード(確認)", validators=[DataRequired()])
    submit = SubmitField("登録")

class LoginForm(FlaskForm):
    username = StringField("ユーザー名", validators=[DataRequired()])
    password = PasswordField("パスワード", validators=[DataRequired(), EqualTo("pass_confirm")])
    pass_confirm = PasswordField("パスワード(確認)", validators=[DataRequired()])
    submit = SubmitField("ログイン")


@app.route("/register_user", methods=["GET", "POST"])
def register_user():
    form = RegistartionForm()
    print("判定：", form.validate_on_submit())
    if form.validate_on_submit():
        #登録しようとしたユーザー名が存在するか確認
        existing_user = User.query.filter_by(username=form.username.data).first()
        print("existing:", existing_user)
        if existing_user:
            flash('このユーザー名は既に使用されています。別のユーザー名を選択してください。', 'error')
            return redirect(url_for('register_user'))
        
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('ユーザー登録が完了しました。ログインしてください。', 'success')
        return redirect(url_for("login"))
    return render_template("register_user.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    print("ログインフォーム判定:", form.validate_on_submit())
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        #ユーザーの認証処理
        user = User.query.filter_by(username=username).first()
        if not user:
            print("ユーザいないよ")
            return render_template("login.html", error_message="ユーザー名またはパスワードが正しくありません")
        if user.check_password(password):
            #ユーザーが正しい場合はセッションにユーザーidを保存
            session["user_id"] = user.id
            return redirect(url_for("index"))
        
    return render_template("login.html", form=form)


#-------------タスク関係-----------------
@app.route("/add_task", methods=["GET", "POST"])
def add_task():
    if request.method == "POST": #POSTメソッドではフォームから送信されたタスクの情報をDBに追加する．
        title = request.form["title"]
        status = request.form["status"]
        creted_date = datetime.date.today()
        new_task = Task(title, status, creted_date)
        db.session.add(new_task)
        db.session.commit()

        return redirect(url_for("index"))
    
    return render_template("add_task.html") #GETメソッドではadd_task.htmlを表示する．

@app.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    task = Task.query.get(task_id)
    print(task_id)
    if task:
        if request.method == "POST":
            task.title = request.form["title"]
            task.status = request.form["status"]
            db.session.commit()
            return redirect(url_for("index"))
        return render_template("edit_task.html", task=task)
    return redirect(url_for("index"))

@app.route("/delete_task/<int:task_id>", methods=["GET","POST"])
def delete_task(task_id):
    print("delete_task_id:",task_id)
    task = Task.query.get(task_id)

    if task:
        db.session.delete(task)
        db.session.commit()
        #flash("タスクが削除されました", "success")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
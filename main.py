from flask import Flask, render_template, request, session, redirect, Markup
from flask_sqlalchemy import SQLAlchemy
import pymysql
from flask_mail import Mail
import math, datetime, json, os, hashlib

with open('./templates/config.json', 'r') as file:
    params = json.load(file)["params"]

local_server = params["local_server"]

app = Flask(__name__)
app.secret_key = "DS"
app.config['Upload_File'] = params['upload_location']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-username'],
    MAIL_PASSWORD=params['gmail-password']
)

mail = Mail(app)

if local_server == str("True"):
    app.config["SQLALCHEMY_DATABASE_URI"] = params["local_uri"]
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["prod_uri"]

db = SQLAlchemy(app)

class Contact(db.Model):
    '''
    sno,name,email,message,phone_number,date
    '''
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String(12), nullable=False)
    date = db.Column(db.String, nullable=True)


class Posts(db.Model):
    '''
    sno,title,tagline,content,slug,date
    '''
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    subtitle = db.Column(db.String, nullable=False)
    content = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=True)
    img_url = db.Column(db.String, nullable=True)
    userid = db.Column(db.String, nullable=False)

class Users(db.Model):
    '''
    userid, userpass, email, firstname, lastname, address1, address2, zipcode, city, state, country, phone
    '''
    userid = db.Column(db.String, primary_key=True)
    userpass = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    firstname = db.Column(db.String, nullable=False)
    lastname = db.Column(db.String, nullable=False)
    address1 = db.Column(db.String, nullable=True)
    address2 = db.Column(db.String, nullable=True)
    zipcode = db.Column(db.String, nullable=True)
    city = db.Column(db.String, nullable=True)
    state = db.Column(db.String, nullable=True)
    country = db.Column(db.String, nullable=True)
    phone = db.Column(db.String, nullable=True)
    

@app.route('/')
def home():
    all_posts = Posts.query.filter_by().order_by(Posts.date.desc()).all()
    # [0:params['no_of_posts']]
    last = math.ceil(len(all_posts)/int(params['no_of_posts']))
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = all_posts[(page-1)*params['no_of_posts']:(page-1) *
                      params['no_of_posts']+params['no_of_posts']]

    if page == 1:
        prev = '#'
        nextp = '/?page='+str(page+1)
    elif(page == last):
        prev = '/?page='+str(page-1)
        nextp = '#'
    else:
        prev = '/?page='+str(page-1)
        nextp = '/?page='+str(page+1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=nextp)


@app.route('/about')
def about():
    return render_template('about.html', params=params)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if(request.method == 'POST'):
        #  ADD Entry to the Database
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        phone_number = request.form.get('phone_number')
        date = datetime.datetime.now()
        entry = Contact(name=name, email=email, date=date,
                        phone_number=phone_number, message=message)

        db.session.add(entry)
        db.session.commit()
        mail.send_message('New Message from Blog', sender=email, recipients=[params['gmail-username']],
                          body=message + '\n' + phone_number
                          )
    return render_template('contact.html', params=params)

@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':

        user = Users(
            userid=request.form['userid'], 
            userpass=hashlib.md5(request.form['userpass'].encode()).hexdigest(), 
            email = request.form['email'],
            firstname = request.form['firstname'],
            lastname = request.form['lastname'],
            address1 = request.form['address1'],
            address2 = request.form['address2'],
            zipcode = request.form['zipcode'],
            city = request.form['city'],
            state = request.form['state'],
            country = request.form['country'],
            phone = request.form['phone']
            )
        db.session.add(user)
        db.session.commit()
        
        return render_template("login.html", params=params)

    return render_template("register.html", params=params)


@app.route('/post/<string:post_slug>', methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    post.content = Markup(post.content)
    return render_template('post.html', params=params, post=post)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    if request.method == 'POST':
        # Redirect to Admin Panel
        userid = request.form.get('user')
        userpass = request.form.get('pass')
        
        user = Users.query.filter_by(userid = userid).first()
        
        if (user.userpass == hashlib.md5(userpass.encode()).hexdigest()):
            # Set the Session variable
            session['user'] = userid
    
    if('user' in session):
        if (session['user'] == params['admin_user']):
            posts = Posts.query.filter_by().all()
        else:
            posts = Posts.query.filter_by(userid=session['user']).all()
        
        params['user'] = session['user']
        return render_template('dashboard.html', params=params, posts=posts)

    return render_template('login.html', params=params)


# @app.route('/edit', methods=['GET', 'POST'])
# def temp():
#     post = Posts.query.filter_by(sno=0).first()
#     return render_template('edit.html', params=params, post=post, sno=0)


@app.route('/edit/<string:sno>', methods=['GET', 'POST'])
def edit(sno=0):
    if('user' in session):
        if request.method == 'POST':
            '''
            title,tagline,slug,image,content
            '''
            title = request.form.get('title')
            subtitle = request.form.get('subtitle')
            slug = request.form.get('slug')
            img = request.form.get('img')
            content = request.form.get('content')

            if sno == '0' or sno == 0:
                post = Posts(title=title, subtitle=subtitle, content=content, slug=slug,
                             img_url=img, date=datetime.datetime.now(), userid = session['user'])
                db.session.add(post)
                db.session.commit()

                return render_template('edit.html', params=params, post=post, sno=sno)

            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.slug = slug
                post.subtitle = subtitle
                post.img_url = img
                post.content = content
                post.date = datetime.datetime.now()

                db.session.add(post)
                db.session.commit()
                return redirect('/edit/'+sno)
                
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if('user' in session):
        if request.method == 'POST':
            f = request.files['file']
            f.save(os.path.join(
                app.config['Upload_File'], f.filename))
            return "Uploaded Successfully !"


@app.route('/delete/<string:sno>', methods=['GET', 'POST'])
def delete(sno):
    if('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')


app.run(host="0.0.0.0", port= os.environ.get("PORT", 5000), debug=False)

from flask import Flask, request, render_template, make_response, redirect, flash
from flask_bootstrap import Bootstrap
from google.appengine.ext import ndb, blobstore
from google.appengine.api import mail, users, images
from google.appengine.ext.webapp import blobstore_handlers
from werkzeug.http import parse_options_header
import json
from datetime import datetime
import logging


def my_render_template(template, **kwargs):
    user = users.get_current_user()
    login_url = users.create_login_url('/')
    logout_url = users.create_logout_url('/')
    return render_template(template,
                           user=user,
                           login_url=login_url,
                           logout_url=logout_url, **kwargs)


class FlowerData(ndb.Model):
    flower_name = ndb.StringProperty()
    grow_session = ndb.StringProperty()
    timestamp = ndb.DateTimeProperty()
    temperature = ndb.FloatProperty()
    light = ndb.IntegerProperty()
    water = ndb.FloatProperty()
    battery = ndb.IntegerProperty()
    ecb = ndb.FloatProperty()
    ec_porus = ndb.FloatProperty()
    dli = ndb.FloatProperty()
    ea = ndb.FloatProperty()

    @classmethod
    def new_from_data(cls, data):
        return FlowerData(
            flower_name=str(data['FlowerName']),
            grow_session=str(data['GrowSession']),
            timestamp=datetime.strptime(data['TimeStamp'], "%Y-%m-%d %H:%M:%S"),
            temperature=float(data['Temperature']),
            light=int(data['Light']),
            water=float(data['Water']),
            battery=int(data['Battery']),
            ecb=float(data['Ecb']),
            ec_porus=float(data['EcPorus']),
            dli=float(data['DLI']),
            ea=float(data['Ea']),
        ).put()


class Picture(ndb.Model):
    picture = ndb.BlobProperty()


class Gif(ndb.Model):
    blob_key = ndb.BlobKeyProperty()


app = Flask(__name__)
app.secret_key = 'asd123'
Bootstrap(app)


@app.route('/flower/new_data', methods=['POST'])
def new_flower_data():
    data = json.loads(request.data)
    logging.info(data)
    FlowerData.new_from_data(data)
    return "Success"


@app.route('/flower/new_picture', methods=['POST'])
def new_flower_picture():
    try:
        file_ = request.files['webcam.jpg']
        ndb.delete_multi(Picture.query().fetch(keys_only=True))
        Picture(picture=file_.stream.read()).put()
    except Exception as e:
        print(e)
    return "Success"


@app.route('/flower/new_gif', methods=['GET', 'POST'])
def new_flower_gif():
    return blobstore.create_upload_url('/upload_gif_finished')


@app.route('/upload_gif_finished', methods=['POST'])
def upload_gif_finished():
    if request.method == 'POST':
        f = request.files['file']
        header = f.headers['Content-Type']
        parsed_header = parse_options_header(header)
        blob_key = parsed_header[1]['blob-key']
        gifs = Gif.query().fetch(5)
        for gif in gifs:
            blobstore.delete(gif.blob_key)
        ndb.delete_multi(Gif.query().fetch(keys_only=True))
        Gif(blob_key=blobstore.blobstore.BlobKey(blob_key)).put()
        return blob_key


@app.route('/email/new', methods=['POST'])
def new_email():
    data = json.loads(request.data)
    logging.info(data)
    mail.send_mail(sender='florian.groetzner@gmail.com',
                   to=data['receiver'],
                   subject=data['subject'],
                   body=data['body'])
    return "Success"


@app.route('/flower/data')
def flower_data():
    data = FlowerData.query().order(FlowerData.timestamp).fetch(1000)
    return my_render_template('data.html', data=data)


@app.route('/flower/picture')
def flower_picture():
    user = users.get_current_user()
    if user:
        if users.is_current_user_admin():
            picture = Picture.query().fetch(1)[0]
            img = images.Image(picture.picture)
            img.im_feeling_lucky()
            output_image = img.execute_transforms(output_encoding=images.JPEG)
            resp = make_response(output_image, 200)
            resp.headers['Content-Type'] = 'image/png'
            return resp
        else:
            flash('Only Admins allowed for Webcam', 'error')
            return my_render_template('index.html')
    return redirect(users.create_login_url('/flower/picture'))


@app.route('/flower/gif')
def flower_gif():
    user = users.get_current_user()
    if user:
        if users.is_current_user_admin():
            gif = Gif.query().fetch(1)[0]
            blob_info = blobstore.get(gif.blob_key)
            response = make_response(blob_info.open().read())
            response.headers['Content-Type'] = blob_info.content_type
            return response
        else:
            flash('Only Admins allowed for Webcam', 'error')
            return my_render_template('index.html')
    return redirect(users.create_login_url('/flower/gif'))


@app.route('/')
def index():
    return my_render_template('index.html')


if __name__ == '__main__':
    app.run()

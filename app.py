import datetime
import functools
import os
import re
import urllib

from flask import (Flask, flash, redirect, render_template, request, Response, session, url_for)
from micawber import bootstrap_basic, parse_html
from peewee import *
from playhouse.flask_utils import FlaskDB, get_object_or_404, object_list
from playhouse.sqlite_ext import *

# config values
ADMIN_PASSWORD = 'secret'
APP_DIR = os.path.dirname(os.path.realpath(__file__))

# the playhouse.flask_utils.FlaskDB object accepts db URL configuration
DATABASE = 'sqliteext:///%s' % os.path.join(APP_DIR, 'reports.db')
DEBUG = False

# secret key used internally by Flask to encrypt session data store in cookies
SECRET_KEY = 'super-secret-squirrels?'

# create Flask WSGI app and configure it
app = Flask(__name__)
app.config.from_object(__name__)

# FlaskDB wrapper for pre/post-request hooks for db connections
flask_db = FlaskDB(app)

# database is the actual database (flask_db is the wrapper)
database = flask_db.database


class Report(flask_db.Model):
    type = CharField()
    location = CharField()
    details = TextField()
    submitted = BooleanField(index=True)
    timestamp = DateTimeField(default=datetime.datetime.now, index=True)

    @property
    def save(self, *args, **kwargs):
        ret = super(Report, self).save(*args, **kwargs)

        return ret

    @classmethod
    def accepted(cls):
        return Report.select().where(Report.submitted == True)

def login_required(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if session.get('logged_in'):
            return fn(*args, **kwargs)
        return redirect(url_for('login', next=request.path))
    return inner

@app.route('/login/', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next')
    if request.method == 'POST' and request.form.get('password'):
        password = request.form.get('password')
        if password == app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            session.permanent = True
            flash('You are now logged in.', 'success')
            return redirect(next_url or url_for('index'))
        else:
            flash('Incorrect password.', 'danger')
    return render_template('login.html', next_url=next_url)

@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.clear()
        return redirect(url_for('index'))
    return render_template('logout.html')

@app.route('/')
def index():
    query = Report.accepted().order_by(Report.timestamp.desc())

    return object_list(
        'index.html',
        query,
        check_bounds=False)

@app.route('/create/', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        if request.form.get('submitted'):
            if request.form.get('type') and request.form.get('location'):
                report = Report.create(
                    type=request.form['type'],
                    location=request.form['location'],
                    details=request.form['details'],
                    submitted=request.form.get('submitted') or False)
                flash('Entry created successfully.', 'success')
                if report.published:
                    return redirect(url_for('detail', id=report.id))
                else:
                    return redirect(url_for('create'))
            else:
                flash('Please fill out all required fields before submitting.', 'danger')
        else:
            flash('You must agree to the terms and conditions before submitting.', 'danger')
    return render_template('create.html')

@app.route('/report/<id>/')
@login_required
def detail(id):
    query = Report.select()
    
    report = get_object_or_404(query, Report.id == id)
    return render_template('detail.html', report=report)

@app.errorhandler(404)
def not_found(exc):
    return Response('<h2>Error 404: Not Found</h2>'), 404

def main():
    database.create_tables([Report], safe=True)
    app.run(host='0.0.0.0',debug=True)

if __name__ == '__main__':
    main()

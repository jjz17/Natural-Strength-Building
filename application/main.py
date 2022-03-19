from flask import Flask, render_template, request, redirect, url_for, session
import joblib
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import io
import os
import _pickle as cPickle
import re


from application import app
from application import forms
from application.base import Session
from application.user import User
from application.user_metrics import UserMetrics

today = date.today()

# Uncomment to run app through this file (main.py)
# app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'your secret key'

# Avoid multithreading MatPlotLib GUI error
plt.switch_backend('Agg')

# Helper functions


def lbs_to_kg(lbs):
    return round(float(lbs) * 0.453592, 2)


def kg_to_lbs(kg):
    return round(float(kg) * 2.20462, 2)


def load_model(model_file: str):
    return cPickle.load(open(model_file, 'rb'))


def scale_stats(scaler, stats: list):
    return scaler.transform(np.array(stats).reshape(1, -1))


# # Load in the models and scalers
bench_model = load_model(f'models{os.path.sep}bench_model.pickle')
bench_scaler = joblib.load(f'models{os.path.sep}bench_scaler')
squat_model = load_model(f'models{os.path.sep}squat_model.pickle')
squat_scaler = joblib.load(f'models{os.path.sep}squat_scaler')
deadlift_model = load_model(f'models{os.path.sep}deadlift_model.pickle')
deadlift_scaler = joblib.load(f'models{os.path.sep}deadlift_scaler')


@app.route('/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']

        db_session = Session()
        # Check exists record with matching username and password
        user_query = db_session.query(User) \
            .filter((User.username == username) & (User.password == password))
        db_session.close()
        # If user exists in users table in the database
        if user_query.count() == 1:
            user = user_query[0]
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = user.id
            session['username'] = user.username
            # Toggles between STANDARD and METRIC
            session['units'] = 'STANDARD'
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # User doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)


@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    # session.pop('loggedin', None)
    # session.pop('id', None)
    # session.pop('username', None)
    session.clear()
    # Redirect to login page
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'birth_date' in request.form and 'email' in request.form and 'sex' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        birth_date = request.form['birth_date']
        email = request.form['email']
        sex = request.form['sex']

        db_session = Session()
        user_query = db_session.query(User) \
            .filter(User.username == username)

        # If user exists show error and validation checks
        if user_query.count() > 0:
            msg = 'User already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            user = User(username, password, birth_date, email, sex)
            db_session.add(user)
            db_session.commit()
            db_session.close()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


# Home page, only accessible for loggedin users
@app.route('/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# Profile page, only accessible for loggedin users
@app.route('/profile', methods=['GET', 'POST'])
# @app.route('/profile/', defaults={'units': ''})
# @app.route('/profile/<units>', methods=['GET', 'POST'])
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the user's info so we can display it on the profile page

        db_session = Session()
        # Select the current user's records in the databse
        user_query = db_session.query(User) \
            .filter(User.id == session['id'])
        db_session.close()
        user = user_query[0]

        if request.method == 'POST' and 'units' in request.form:
            # Create variables for easy access
            units = request.form['units']
            session['units'] = units
        # Show the profile page with user info
        return render_template('profile.html', user=user)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/test')
def test():
    return session['units']


# Profile update page, only accessible for loggedin users
@app.route('/update', methods=['GET', 'POST'])
def update():
    # Check if user is loggedin
    if 'loggedin' in session:
        id = session['id']

        # Create a new session
        db_session = Session()

        # Output message if something goes wrong...
        msg = ''
        user = None
        # Check if "username", "password" and "email" POST requests exist (user submitted form)
        if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
            # Create variables for easy access
            username = request.form['username']
            password = request.form['password']
            birth_date = request.form['birth_date']
            # weight = request.form['weight']
            # squat = request.form['squat']
            # bench = request.form['bench']
            # deadlift = request.form['deadlift']
            email = request.form['email']

            # Validation checks
            if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                msg = 'Invalid email address!'
            elif not re.match(r'[A-Za-z0-9]+', username):
                msg = 'Username must contain only characters and numbers!'
            elif not username or not password or not email:
                msg = 'Please fill out the form!'
            # elif not re.match(r'^\+?(0|[1-9]\d*)$', birth_date):
                # msg = 'Birth date must be a valid date in the form MM/DD/YYYY'
            # elif not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', weight):
            #     msg = 'Weight must be a positive number'
            # elif not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', squat):
            #     msg = 'Squat must be a positive number'
            # elif not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', bench):
            #     msg = 'Bench must be a positive number'
            # elif not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', deadlift):
            #     msg = 'Deadlift must be a positive number'
            else:
             # User doesn't exist and the form data is valid, now update data into users table
                user = db_session.query(User).get(id)
                user.username = username
                user.password = password
                user.birth_date = birth_date
                user.email = email
                db_session.commit()
                db_session.close()
                msg = 'You have successfully updated!'
        elif request.method == 'POST':
            # Form is empty... (no POST data)
            msg = 'Please fill out the form!'

        # Show the update form with message (if any)
        return render_template('update.html', msg=msg)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# Metrics insert page, only accessible for loggedin users
# @app.route('/metrics', methods=['GET', 'POST'])
@app.route('/metrics/<metric>', methods=['GET', 'POST'])
def metrics(metric):
    # Check if user is loggedin
    if 'loggedin' in session:
        id = session['id']

        # Create a new session
        db_session = Session()

        # Output message if something goes wrong...
        msg = ''
        user = db_session.query(User).get(id)
        # Check if "username", "password" and "email" POST requests exist (user submitted form)
        if request.method == 'POST' and 'weight' in request.form and 'squat' in request.form and 'bench' in request.form and 'deadlift' in request.form:
            # Create variables for easy access
            weight = request.form['weight']
            squat = request.form['squat']
            bench = request.form['bench']
            deadlift = request.form['deadlift']
            date = request.form['date']

            # Convert metrics to be inserted
            if session['units'] == 'METRIC':
                weight = kg_to_lbs(weight)
                squat = kg_to_lbs(squat)
                bench = kg_to_lbs(bench)
                deadlift = kg_to_lbs(deadlift)

            # Validation checks
            # if not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', weight):
            #     msg = 'Weight must be a positive number'
            # elif not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', squat):
            #     msg = 'Squat must be a positive number'
            # elif not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', bench):
            #     msg = 'Bench must be a positive number'
            # elif not re.match(r'^(0*[1-9][0-9]*(\.[0-9]+)?|0+\.[0-9]*[1-9][0-9]*)$', deadlift):
            #     msg = 'Deadlift must be a positive number'
            # else:
            metrics_query = db_session.query(UserMetrics) \
                .filter((UserMetrics.date == date) & (UserMetrics.user == user))

            # If entry exists for this day, update it
            if metrics_query.count() == 1:
                metrics = metrics_query[0]
                metrics.weight = weight
                metrics.squat = squat
                metrics.bench = bench
                metrics.deadlift = deadlift
            # Else insert new metrics record
            else:
                metrics = UserMetrics(
                    user, weight, squat, bench, deadlift, date)
                db_session.add(metrics)
            db_session.commit()
            db_session.close()
            msg = 'You have successfully inserted your data!'
        elif request.method == 'POST':
            # Form is empty... (no POST data)
            msg = 'Please fill out the form!'

        pred = ''
        difference_in_years = None
        stats = None
        # Check if metric prediction is requested
        if metric != 'none':
            stats = db_session.query(UserMetrics) \
                .order_by(UserMetrics.date.desc())
            if stats.count() > 0:
                stats = stats[0]

                # Parse out stats
                weight = stats.weight
                squat = stats.squat
                bench = stats.bench
                deadlift = stats.deadlift

                # Calculate user age
                age = relativedelta(today, user.birth_date).years

                # Determine user sex
                male = 0
                female = 0
                if user.sex == 0:
                    male = 1
                elif user.sex == 1:
                    female = 1
                else:
                    pass

                if metric == 'squat':
                    input = scale_stats(squat_scaler, [age, weight, bench, deadlift, female, male])
                    pred = squat_model.predict(np.array(input).reshape(1,-1))[0]
                elif metric == 'bench':
                    input = scale_stats(bench_scaler, [age, weight, squat, deadlift, female, male])
                    pred = bench_model.predict(np.array(input).reshape(1,-1))[0]
                elif metric == 'deadlift':
                    input = scale_stats(deadlift_scaler, [age, weight, bench, squat, female, male])
                    pred = deadlift_model.predict(np.array(input).reshape(1,-1))[0]
                else:
                    pass
            else:
                pred = 'No data'

        # Show the update form with message (if any)
        return render_template('metrics.html', msg=msg, pred=pred)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/wtforms', methods=['GET', 'POST'])
def wtforms():
    name = None
    form = forms.NamerForm()
    if form.validate_on_submit():
        name = form.name.data
        form.name.data = ''
    return render_template('wtforms.html', name=name, form=form)


# Displays the plot of the requested user metric
@app.route('/chart/<metric>', methods=['GET'])
def chart_metric(metric):
    title = f'Your Custom {metric.title()} Plot'
    plot = plot_metric(metric)
    return render_template('plot.html', title=title, plot=plot)


def plot_metric(metric):
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    FigureCanvas(fig)

    db_session = Session()

    user_metrics = db_session.query(UserMetrics) \
        .filter(UserMetrics.user_id == session['id']) \
        .order_by(UserMetrics.date.asc())

    dates = [user_metric.date for user_metric in user_metrics]
    metric_list = [getattr(user_metric, metric)
                   for user_metric in user_metrics]

    # Convert metrics data to metric units to plot
    if session['units'] == 'METRIC':
        metric_list = [lbs_to_kg(metric) for metric in metric_list]

    ax.plot(dates, metric_list)

    ax.set_xlabel('Time')
    ax.set_ylabel(metric.title())
    # ax.set_title(f'There are {points} data points!')
    ax.grid(True)

    # Rotate x-axis labels to fit on chart
    plt.setp(ax.get_xticklabels(), rotation=30, horizontalalignment='right')

    # Make room for x and y labels
    plt.tight_layout()

    # fig, (ax1, ax2) = plt.subplots(1, 2)
    # fig.suptitle('Horizontally stacked subplots')
    # x = data[:, 0]
    # y = data[:, 1]
    # ax1.plot(x, y)
    # ax2.plot(x, -y)

    img = io.StringIO()
    fig.savefig(img, format='svg')
    # clip off the xml headers from the image
    svg_img = '<svg' + img.getvalue().split('<svg')[1]

    return svg_img


@app.route('/plot/<int:points>', methods=['GET'])
def plot(points):
    title = 'Randomly Generated Scatterplot'
    plot = plot_points(points)
    return render_template('plot.html', title=title, plot=plot)


def plot_points(points):
    """Generate a plot with a varying number of randomly generated points
    Args:
    points (int): a number of points to plot
    Returns: An svg plot with <points> data points
    """
    # data for plotting
    data = np.random

    data = np.random.rand(points, 2)

    fig = Figure()
    FigureCanvas(fig)

    ax = fig.add_subplot(111)

    ax.scatter(data[:, 0], data[:, 1])

    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title(f'There are {points} data points!')
    ax.grid(True)

    img = io.StringIO()
    fig.savefig(img, format='svg')
    # clip off the xml headers from the image
    svg_img = '<svg' + img.getvalue().split('<svg')[1]

    return svg_img


# Uncomment to run app through this file (main.py)
# if __name__ == '__main__':
#     app.run()
    # app.run(host='0.0.0.0', port=5000)

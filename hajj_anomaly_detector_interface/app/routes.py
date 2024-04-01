from flask import render_template, request, redirect, url_for, flash
from app import app, db, bcrypt
from app.forms import PredictionForm, RegistrationForm, LoginForm, UpdateAccountForm, ContactForm
from app.models import User, Record
from flask_login import login_user, current_user, logout_user, login_required

import os
from app.Utils import Utils

@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    form = PredictionForm()
    if form.validate_on_submit():
        return redirect(url_for('predict'))
    return render_template('index.html', title="Home", form=form), 200

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        FILE_NAME = 'uploadedImage'
        if FILE_NAME not in request.files:
            return render_template('error1.html', title='File Error', code=406, message='No file selected', description='Please select a file to upload'), 406

        image = request.files[FILE_NAME]

        image_name = Utils.save_image(image, app.root_path, folder_name='records', resize=False)
        image_path = os.path.join(app.root_path, 'static/images/records', image_name)

        predicted = Utils.load_model(root_path=app.root_path).predict(Utils.preprocess_image(image_path))

        data = list(zip(Utils.get_labels(), predicted[0].tolist()))

        return render_template('predict.html', title='Image Prediction Result', data=data, image_name=image_name, labels=Utils.get_labels(), predicted=predicted[0].tolist()), 200
    else:
        return render_template('error1.html', title='Method Not Allowed', code=405, message='Method Not Allowed', description='The method you are trying to use is not allowed'), 405

@app.route('/record/<int:record_id>', methods=['GET'])
@login_required
def record(record_id):
    record = Record.query.get(record_id)
    if not record:
        return render_template('error1.html', title='Record Not Found', code=404, message='Record Not Found', description='The record you are looking for does not exist.'), 404
    # Convert the string to list
    predicted = record.prediction = list(map(float, record.prediction[1:-1].split(',')))
    data = list(zip(Utils.get_labels(), predicted))
    return render_template('record.html', title=f'{record.created_at} result', data=data, image_name=record.image_name, labels=Utils.get_labels(), predicted=predicted), 200

@app.route('/records', methods=['GET'])
@login_required
def records():
    records = Record.query.filter_by(creator=current_user).all()
    if not records:
        flash('No records found.', 'info')
        return redirect(url_for('index'))
    return render_template('records.html', title='Records', records=records), 200

@app.route('/record/new', methods=['POST'])
@login_required
def new_record():
    image_name = request.form.get('image_name')
    predicted = request.form.get('predicted')
    note = request.form.get('note')
    # validate the image_name and predicted
    if not image_name or not predicted:
        return render_template('error1.html', title='Bad Request', code=400, message='Bad Request', description='The request you sent is invalid'), 400
    # validate the note
    DEFAULT_NOTE = 'Add some notes.(Optional)'
    if note == DEFAULT_NOTE or not note:
        note = 'No notes.'
        
    record = Record(image_name=image_name, prediction=predicted, note=note, creator=current_user)
    db.session.add(record)
    try:
        db.session.commit()
        flash('Your record has been saved!', 'success')
        return redirect(url_for('records'))
    except:
        db.session.rollback()
        flash('An error occurred while saving your record. Please try again later.', 'danger')
        return redirect(url_for('index'))
    
@app.route('/record/<int:record_id>/delete', methods=['GET'])
@login_required
def delete_record(record_id):
    record = Record.query.get(record_id)
    if not record:
        return render_template('error1.html', title='Record Not Found', code=404, message='Record Not Found', description='The record you are looking for does not exist.'), 404
    # validate the creator
    if record.creator != current_user:
        return render_template('error1.html', title='Unauthorized', code=401, message='Unauthorized', description='You are not authorized to delete this record.'), 401
    db.session.delete(record)
    try:
        db.session.commit()
        flash('Your record has been deleted!', 'success')
        return redirect(url_for('records'))
    except:
        db.session.rollback()
        flash('An error occurred while deleting your record. Please try again later.', 'danger')
        return redirect(url_for('records'))

@app.route('/about')
def about():
    return render_template('about.html', title='About'), 200

@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        flash('Your message has been sent!', 'success')
        return redirect(url_for('contact'))
    elif request.method == 'GET':
        form.name.data = current_user.username
        form.email.data = current_user.email
    return render_template('contact.html', title='Contact', form=form), 200

@app.route('/faq')
def faq():
    return render_template('faq.html', title='FAQ'), 200


# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        try:
            db.session.commit()
            flash(f'Your account has been created!', 'success')
            login_user(user)
            return redirect(url_for('index'))
        except:
            db.session.rollback()
            flash(f'An error occurred while creating your account. Please try again later.', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html', title='Register', form=form), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash(f'Login failed. Please check your email and password.', 'danger')
    return render_template('login.html', title='Login', form=form), 200

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            # TODO: Delete the old image
            image_name = Utils.save_image(form.picture.data, app.root_path)
            current_user.image_file = image_name
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='images/profile_pics/' + current_user.image_file)
    return render_template('profile.html', title='Profile', image_file=image_file, form=form), 200

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    random_number = Utils.generate_random_number(1, 5)
    return render_template(f'error{random_number}.html', title='Page Not Found', code=404, message="The page you are looking for does not exist.", description=""), 404

# Unauthorized access handling
@app.errorhandler(401)
def unauthorized_access(e):
    return render_template('unauthorized.html', title='Unauthorized'), 401
from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db, bcrypt
from app.forms import PredictionForm, UpdatePredictionForm, RegistrationForm, LoginForm, UpdateAccountForm, ContactForm
from app.models import User, Record
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.datastructures import FileStorage
from PIL import Image

import os
from app.Utils import Utils

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def index():
    form = PredictionForm()
    if form.validate_on_submit():
        image: FileStorage = form.uploadedImage.data

        if not Utils.validate_file(image, allowed_extensions=['jpg', 'jpeg', 'png']):
            return render_template('error1.html', title='File Error', code=406, message='Invalid Extension', description='Please select a valid file type (jpg, jpeg, png)'), 406
  
        RECORD_SAVE_PATH = os.path.join(app.root_path, 'static/images/records')

        image_name = Utils.save_image(image, path=RECORD_SAVE_PATH, resize=False)
        image_path = os.path.join(RECORD_SAVE_PATH, image_name)

        # Classification using InceptionV3 model
        inceptionv3_model_path = os.path.join(app.root_path, 'static/models/inceptionv3.h5')
        inceptionv3 = Utils.load_model(model_path=inceptionv3_model_path, model_type=Utils.KERAS)
        predicted = Utils.predict(inceptionv3, image_path).astype(int)

        # Image Localization using YOLOv8 model
        LOCALIZED_SAVE_PATH = os.path.join(app.root_path, 'static/images/localized')
        yolov8_model_path = os.path.join(app.root_path, 'static/models/best.pt')
        confidence_threshold = float(form.confidence.data)

        yolov8 = Utils.load_model(model_path=yolov8_model_path, model_type=Utils.YOLO)
        localized_image_name = Utils.localize(yolov8, image_path, output_path=LOCALIZED_SAVE_PATH, confidence_threshold=confidence_threshold)

        # Remove the uploaded image
        os.remove(image_path)

        data = list(zip(Utils.get_labels(), predicted))

        return render_template('predict.html', title='Image Prediction Result', data=data, image_name=localized_image_name, labels=Utils.get_labels(), predicted=predicted), 200

    return render_template('index.html', title="Home", form=form), 200


@app.route('/predict', methods=['POST'])
def predict():
    return jsonify({'message': 'This is a prediction route'}), 200

@app.route('/record/<int:record_id>', methods=['GET'])
@login_required
def record(record_id):
    form = UpdatePredictionForm()
    record: Record = Record.query.get(record_id)

    if not record or record.creator != current_user:
        return render_template('error1.html', title='Record Not Found', code=404, message='Record Not Found', description='The record you are looking for does not exist.'), 404

    if form.validate_on_submit():
        record.notes = form.notes.data
        try:
            db.session.commit()
            flash('Prediction notes has been updated!', 'success')
        except:
            db.session.rollback()
            flash('An error occurred while Updating prediction notes. Please try again later.', 'danger')
        return redirect(url_for('records'))
    else:
        # Convert the string to list
        predicted = list(map(float, record.prediction[1:-1].split(' ')))
        data = list(zip(Utils.get_labels(), predicted))
        form.notes.data = record.notes
        return render_template('record.html', title='Record', data=data, record=record, labels=Utils.get_labels(), predicted=predicted, form=form), 200

@app.route('/records', methods=['GET'])
@login_required
def records():
    page = request.args.get('page', 1, type=int)
    records = Record.query.filter_by(creator=current_user).order_by(Record.created_at.desc()).paginate(page=page, per_page=5)
    if not records:
        flash('No records found.', 'info')
        return redirect(url_for('index'))
    return render_template('records.html', title='Records', records=records), 200

@app.route('/record/new', methods=['POST'])
@login_required
def new_record():
    image_name = request.form.get('image_name')
    predicted = request.form.get('predicted')
    notes = request.form.get('notes')
    # validate the image_name and predicted
    if not image_name or not predicted:
        return render_template('error1.html', title='Bad Request', code=400, message='Bad Request', description='The request you sent is invalid'), 400
        
    record = Record(image_name=image_name, prediction=predicted, notes=notes, creator=current_user)
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
    if not record or record.creator != current_user:
        return render_template('error1.html', title='Record Not Found', code=404, message='Record Not Found', description='The record you are looking for does not exist.'), 404
    
    db.session.delete(record)
    try:
        db.session.commit()
        flash('Your record has been deleted!', 'success')
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

@app.route('/guide')
def guide():
    return render_template('guide.html', title='Guide'), 200

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
            flash('Your account has been created!', 'success')
            login_user(user)
            return redirect(url_for('index'))
        except:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again later.', 'danger')
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
            flash('Login failed. Please check your email and password.', 'danger')
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
    records_count = Record.query.filter_by(creator=current_user).count()
    return render_template('profile.html', title='Profile', image_file=image_file, records_count=records_count, form=form), 200

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    random_number = Utils.generate_random_number(1, 5)
    return render_template(f'error{random_number}.html', title='Page Not Found', code=404, message="The page you are looking for does not exist.", description=""), 404

# Unauthorized access handling
@app.errorhandler(401)
def unauthorized_access(e):
    return render_template('unauthorized.html', title='Unauthorized'), 401
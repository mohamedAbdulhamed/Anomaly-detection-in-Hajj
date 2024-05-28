from app import app, db

if __name__ == '__main__':
    # app.run(debug=True, host='127.0.0.1', port=7070)
    with app.app_context():
        db.create_all()

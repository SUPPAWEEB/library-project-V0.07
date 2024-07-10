
from flask import Flask,request,jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String,Column,Boolean
from sqlalchemy.exc import OperationalError 
import sqlite3
import jwt
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import ForeignKey,DateTime
from sqlalchemy.orm import relationship
from flask_cors import CORS  
from functools import wraps


con =sqlite3.connect("library.db",check_same_thread=False)
cur = con.cursor()
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'I love books' 
app.config['JWT_ALGORITHM'] = 'HS256' 
jwt = JWTManager(app)
db = SQLAlchemy(app)




class User(db.Model):
    id: Column[int] = Column(Integer, primary_key=True)
    username: Column[str] = Column(String(50), unique=True, nullable=False)
    email: Column[str] = Column(String(120), unique=True, nullable=False)
    password_hash: Column[str] = Column(String(128), nullable=False)
    is_admin: Column[bool] = Column(Boolean, default=False, nullable=False)
    age: Column[int]= Column(Integer)
    name:Column[str] = Column(String(50), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def toggle_admin_status(self, access_key):
        # Replace 'correct_access_key' with your actual secret key
        if access_key == 'simon is king':
            self.is_admin = True
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


# Book model
class Book(db.Model):
    id: Column[int] = Column(Integer, primary_key=True)
    genre: Column[str] = Column(String(20), unique=True, nullable=False)
    title: Column[str] = Column(String(80), unique=True, nullable=False)
    author: Column[str] = Column(String(20), unique=True, nullable=False)
    status: Column[str] = Column(String(20), nullable=False)
    loan_type: Column[int] = Column(Integer, nullable=False)  # Add loan_type field here

    def __repr__(self):
        return f"Book('{self.genre}', '{self.title}', '{self.author}', '{self.status}')"


# Loan model
class Loan(db.Model):
    id: Column[int] = Column(Integer, primary_key=True)
    user_id: Column[int] = Column(Integer, ForeignKey('user.id'), nullable=False)
    book_id: Column[int] = Column(Integer, ForeignKey('book.id'), nullable=False)
    loan_date: Column[DateTime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    return_date: Column[DateTime] = Column(DateTime, nullable=False)
    loan_status: Column[bool] = Column(Boolean, default=True, nullable=False)

    user = relationship("User", backref="loans")
    book = relationship("Book", backref="loans")

    def calculate_return_date(self) -> datetime:
        loan_duration = {
            1: timedelta(weeks=1),
            2: timedelta(weeks=2),
            3: timedelta(weeks=3),
            4: timedelta(weeks=4),
            5: timedelta(weeks=5),
            6: timedelta(weeks=6),
            7: timedelta(weeks=7),
            8: timedelta(weeks=8),
            9: timedelta(weeks=9),
            10: timedelta(weeks=10),
        }

        return self.loan_date + loan_duration.get(self.book.loan_type, timedelta(weeks=1))

    def __repr__(self) -> str:
        return f"Loan(user_id={self.user_id}, book_id={self.book_id}, loan_date={self.loan_date}, return_date={self.return_date})"

    def __init__(self, user_id: int, book_id: int) -> None:
        self.user_id = user_id
        self.book_id = book_id
        self.loan_date = datetime.utcnow()
        self.return_date = self.calculate_return_date()

    def update_loan_status(self, new_status: bool) -> None:
        self.loan_status = new_status
        db.session.commit()

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'loan_date': self.loan_date.strftime("%Y-%m-%d %H:%M:%S"),
            'return_date': self.return_date.strftime("%Y-%m-%d %H:%M:%S"),
            'loan_status': self.loan_status
        }



@app.route("/register", methods=["POST"])
def add_user():
    if request.method == "POST":
        username = request.json.get("username")
        email = request.json.get("email")
        password = request.json.get("password")
        age = request.json.get("age")
        name = request.json.get("name")
        access_key = request.json.get("access_key")  # New field for access_key

        if not username or not email or not password or not age or not name:
            return jsonify({"message": "Missing required fields"}), 400

        # Check if access_key matches admin access key
        is_admin = False
        if access_key == 'simon is king':
            is_admin = True

        try:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({"message": "Username already exists"}), 400

            new_user = User(username=username, email=email, age=age, name=name, is_admin=is_admin)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            return jsonify({"message": "User created successfully"}), 201
        except Exception as e:
            return jsonify({"message": f"Error creating user: {str(e)}"}), 500

@app.route("/user/login", methods=["POST"])
def user_login():
    if request.method == "POST":
        username = request.json.get("username")
        password = request.json.get("password")

        if not username or not password:
            return jsonify({"message": "Missing username or password"}), 400

        try:
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                return jsonify({"message": "Invalid username or password"}), 401

    
            access_token = create_access_token(identity=user.id, expires_delta=timedelta(days=1))
            return jsonify({"access_token": access_token}), 200
        except Exception as e:
            return jsonify({"message": f"Error logging in: {str(e)}"}), 500

#  main page that shows all the books 
@app.route("/all_books", methods=["GET"])
def get_books():
    try:
        books = Book.query.all()
        return jsonify({
            'books': [{'id': book.id,
            'genre': book.genre,
            'title': book.title,
            'author': book.author,
            'status': book.status} for book in books]})
    except OperationalError as e:
        return jsonify({"message": f"Error fetching books: {str(e)}"}), 500
    
# users profile page and loan history 
@app.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin,
        'age': user.age,
        'name': user.name
    }), 200

@app.route('/user/loans', methods=['GET'])
@jwt_required()
def get_user_loans():
    current_user_id = get_jwt_identity()
    loans = Loan.query.filter_by(user_id=current_user_id).all()
    
    if not loans:
        return jsonify({'message': 'No loans found for this user'}), 404
    
    return jsonify({'loans': [loan.serialize() for loan in loans]}), 200

 # routes for loaning and returning books 
@app.route('/return_loan', methods=['PUT'])
@jwt_required()
def return_loan():
    current_user_id = get_jwt_identity()
    user = User.query.filter_by(id=current_user_id).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    loan_id = request.json.get('loan_id')
    if not loan_id:
        return jsonify({'message': 'Missing loan_id parameter'}), 400

    try:
        loan = Loan.query.filter_by(id=loan_id, user_id=current_user_id).first()
        if not loan:
            return jsonify({'message': 'Loan not found'}), 404
        
        loan.update_loan_status(False)
        return jsonify({'message': 'Loan marked as returned successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Error returning loan: {str(e)}'}), 500

@app.route('/new_loan', methods=['POST'])
@jwt_required()
def new_loan():
    user_id = get_jwt_identity()
    book_id = request.json.get('book_id')

    if not book_id:
        return jsonify({'message': 'Missing book_id'}), 400
    
    try:
        user = User.query.filter_by(id=user_id).first()
        book = Book.query.filter_by(id=book_id).first()

        if not user:
            return jsonify({'message': 'User not found'}), 404
        if not book:
            return jsonify({'message': 'Book not found'}), 404
        
        print(f"Creating loan for user {user_id} and book {book_id}")

        new_loan = Loan(user_id=user_id, book_id=book_id)
        db.session.add(new_loan)
        db.session.commit()

        return jsonify({'message': 'Loan created successfully'}), 201
    except Exception as e:
        return jsonify({'message': f'Error creating loan: {str(e)}'}), 500


# Custom decorator for admin authorization
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.filter_by(id=current_user_id).first()
        if not user or not user.is_admin:
            return jsonify({"message": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

# admin only routes 
@app.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def get_users():
    try:
        with app.app_context():
            users = User.query.all()
            return jsonify({'users': [{'id': user.id, 'username': user.username, 'email': user.email} for user in users]})
    except OperationalError as e:
        return jsonify({"message": f"Error fetching users: {str(e)}"}), 500
    

@app.route("/users/delete/<int:user_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_user(user_id):
    try:
        with app.app_context():
            user = User.query.get(user_id)
            if not user:
                return jsonify({"message": "User not found"}), 404

            db.session.delete(user)
            db.session.commit()
            return jsonify({"message": "User deleted successfully"}), 200
    except OperationalError as e:
        return jsonify({"message": f"Error deleting user: {str(e)}"}), 500
    

@app.route("/users/update/<int:user_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_user(user_id):
    if request.method == "PUT":
        username = request.json.get("username")
        email = request.json.get("email")
        age = request.json.get("age")
        name = request.json.get("name")

        try:
            with app.app_context():
                user = User.query.get(user_id)
                if not user:
                    return jsonify({"message": "User not found"}), 404

                # Update user fields if provided
                if username:
                    user.username = username
                if email:
                    user.email = email
                if age:
                    user.age = age
                if name:
                    user.name = name

                db.session.commit()
                return jsonify({"message": "User updated successfully"}), 200
        except OperationalError as e:
            return jsonify({"message": f"Error updating user: {str(e)}"}), 500


@app.route("/books/create", methods=["POST"])
@jwt_required()
@admin_required
def add_book():
    if request.method == "POST":
        genre = request.json.get("genre")
        title = request.json.get("title")
        author = request.json.get("author")
        status = request.json.get("status")
        loan_type = request.json.get("loan_type")  # New field from Book class structure

        if not genre or not title or not author or not status or not loan_type:
            return jsonify({"message": "Missing required fields"}), 400

        try:
            new_book = Book(genre=genre, title=title, author=author, status=status, loan_type=loan_type)
            db.session.add(new_book)
            db.session.commit()
            return jsonify({"message": "Book created successfully"}), 201
        except OperationalError as e:
            return jsonify({"message": f"Error creating book: {str(e)}"}), 500

@app.route("/books/update/<int:book_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update_book(book_id):
    if request.method == "PUT":
        genre = request.json.get("genre")
        title = request.json.get("title")
        author = request.json.get("author")
        status = request.json.get("status")
        loan_type = request.json.get("loan_type")

        try:
            book = Book.query.get(book_id)
            if not book:
                return jsonify({"message": "Book not found"}), 404

            book.genre = genre if genre is not None else book.genre
            book.title = title if title is not None else book.title
            book.author = author if author is not None else book.author
            book.status = status if status is not None else book.status
            book.loan_type = loan_type if loan_type is not None else book.loan_type

            db.session.commit()
            return jsonify({"message": "Book updated successfully"}), 200
        except OperationalError as e:
            return jsonify({"message": f"Error updating book: {str(e)}"}), 500

@app.route("/books/delete/<int:book_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_book(book_id):
    try:
        book = Book.query.get(book_id)
        if not book:
            return jsonify({"message": "Book not found"}), 404

        db.session.delete(book)
        db.session.commit()
        return jsonify({"message": "Book deleted successfully"}), 200
    except OperationalError as e:
        return jsonify({"message": f"Error deleting book: {str(e)}"}), 500

@app.route('/loans', methods=['GET'])
@jwt_required()
@admin_required
def get_loans():
    try:
        loans = Loan.query.all()
        return jsonify({'loans': [loan.serialize() for loan in loans]})
    except OperationalError as e:
        return jsonify({"message": f"Error fetching loans: {str(e)}"}), 500

@app.route('/loans/update/<int:loan_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_loan(loan_id):
    if request.method == 'PUT':
        book_id = request.json.get('book_id')
        return_date = request.json.get('return_date')

        try:
            loan = Loan.query.get(loan_id)
            if not loan:
                return jsonify({"message": "Loan not found"}), 404

            # Update loan fields if provided
            if book_id:
                loan.book_id = book_id
            if return_date:
                loan.return_date = datetime.strptime(return_date, "%Y-%m-%d %H:%M:%S")

            db.session.commit()
            return jsonify({"message": "Loan updated successfully"}), 200
        except OperationalError as e:
            return jsonify({"message": f"Error updating loan: {str(e)}"}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
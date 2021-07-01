from flask import Flask, render_template, redirect, abort, url_for, flash, sessions
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relation, relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
import os
from random import choice
from forms import *

# APP CONFIG
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",  "sqlite:///todolist.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# DB CONFIG
helper_association_table = db.Table("helper association",
                                    db.Column("lists_id", db.Integer,
                                              db.ForeignKey("lists.id")),
                                    db.Column("users_id", db.Integer,
                                              db.ForeignKey("users.id"))
                                    )


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    lists = relationship("ToDoList", back_populates="author",
                         cascade="all, delete-orphan")
    helper_lists = relationship("ToDoList", secondary=helper_association_table)


class ToDoList(db.Model):
    __tablename__ = "lists"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="lists")
    items = relationship("Item", back_populates="list_",
                         cascade="all, delete-orphan")
    date_created = db.Column(db.String(100), nullable=False)
    authorized_users = relationship("User", secondary=helper_association_table)


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey("lists.id"))
    list_ = relationship("ToDoList", back_populates="items")
    content = db.Column(db.String(300), nullable=False)
    date_added = db.Column(db.String(100), nullable=False)


db.create_all()


# LOGIN MANAGER CONFIG
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# ROUTES
@app.route("/")
def home():
    """Renders the home page. If the user is logged in, displays a random 
    greeting message. Page index controls which element is considered 
    'active' in the navbar."""
    GREETINGS = ["Make some lists and whatnot", "Organise your life",
                 "Plan your day", "Time to make some lists", "LISTS", 
                 "You look lovely", "Get organised", "Cool socks", 
                 "Mmmm lists", "Please hire me"]
    return render_template("index.html", greeting=choice(GREETINGS), page_index=0)


@app.route("/enlist", methods=["GET", "POST"])
def enlist():
    """Renders the account creation page. Adds new users to the database
    providing that the data entered in the form is valid."""
    form = EnlistForm()
    if form.validate_on_submit():
        email = form.email.data
        if User.query.filter_by(email=email).first():
            flash("You've already enlisted with that email address. Login instead.")
            return redirect(url_for("login"))
        hashed_and_salted_password = generate_password_hash(
            form.password.data,
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            email=email,
            password=hashed_and_salted_password,
            name=form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("my_lists"))
    return render_template("enlist.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Renders login page. Logs user in."""
    form = LoginForm()
    if form.validate_on_submit():
        # Login and validate the user.
        # user should be an instance of your `User` class
        user_email = form.email.data
        user = User.query.filter_by(email=user_email).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("my_lists"))
            flash("Incorrect password.")
            return render_template("login.html", form=form)
        flash("The email you entered doesn't exist within the database.")
    return render_template("login.html", form=form)


@app.route("/my-lists", methods=["GET", "POST"])
@login_required
def my_lists():
    """Renders the my lists page, which shows all of the current users lists.
    New lists can also be created and added to the database from this page.
    Page index controls which element is considered 'active' in the navbar."""
    form = NewListForm()
    if form.validate_on_submit():
        new_list = ToDoList(
            author=current_user,
            name=form.name.data,
            date_created=datetime.now().strftime("%d-%m-%Y"),
            authorized_users=[]
        )
        db.session.add(new_list)
        db.session.commit()
        return redirect(url_for("show_list", list_id=new_list.id))
    return render_template("my-lists.html", user=current_user, form=form, page_index=1)


@app.route("/enlist-help/<int:list_id>", methods=["GET", "POST"])
def add_authorized_user(list_id):
    requested_list = ToDoList.query.get(list_id)
    # Check if current user is the author of the list they are
    # trying to access.
    if requested_list.author == current_user:
        # if yes then show, if not then abort with 403 (access denied).
        form = EnlistHelpForm()
        if form.validate_on_submit():
            if user_to_add := User.query.filter_by(email=form.email.data).first():
                if user_to_add not in requested_list.authorized_users and user_to_add != current_user:
                    requested_list.authorized_users.append(user_to_add)
                    db.session.commit()
                    return redirect(url_for("add_authorized_user", list_id=list_id))
                flash("That user can already edit this list.")
                return redirect(url_for("add_authorized_user", list_id=list_id))
            flash(
                "No user with that email in the database.\nDid you make a typo you silly billy?")
            return redirect(url_for("add_authorized_user", list_id=list_id))
        return render_template("add-authorized-user.html", list_=requested_list, form=form)
    return abort(403)


@app.route("/fire-helper/<int:list_id>/<int:user_id>", methods=["GET", "POST"])
def remove_authorized_user(list_id, user_id):
    requested_list = ToDoList.query.get(list_id)
    user_to_remove = User.query.get(user_id)
    # Check if current user is the author of the list they are
    # trying to modify permissions for.
    if requested_list.author == current_user:
        # if yes then remove user, if not then abort with 403 (access denied).
        requested_list.authorized_users.remove(user_to_remove)
        db.session.commit()
        return redirect(url_for("add_authorized_user", list_id=list_id))
    return abort(403)


@app.route("/list/<int:list_id>", methods=["GET", "POST"])
@login_required
def show_list(list_id):
    """Shows a specific list where it can be edited, provided that
    the current user is the lists creator."""
    requested_list = ToDoList.query.get(list_id)
    # Check if current user is the author of the list they are
    # trying to access.
    if requested_list.author == current_user or current_user in requested_list.authorized_users:
        # if yes then show, if not then abort with 403 (access denied).
        form = AddItemForm()
        if form.validate_on_submit():
            new_item = Item(
                list_=requested_list,
                content=form.content.data,
                date_added=datetime.now().strftime("%d-%m-%Y")
            )
            db.session.add(new_item)
            db.session.commit()
            return redirect(url_for("show_list", list_id=list_id))
        return render_template("list.html", list_=requested_list, form=form), 200
    return abort(403)


@app.route("/delete-item/<int:list_id>/<int:item_id>", methods=["GET", "POST"])
@login_required
def delete_item(list_id, item_id):
    """Deletes an item from the db if the current user is the author of the list."""
    related_list = ToDoList.query.get(list_id)
    if related_list.author == current_user or current_user in related_list.authorized_users:
        item_to_delete = Item.query.get(item_id)
        db.session.delete(item_to_delete)
        db.session.commit()
        return redirect(url_for("show_list", list_id=list_id))
    return abort(403)


@app.route("/confirm-deletion/<int:list_id>")
@login_required
def confirm_list_deletion(list_id):
    list_to_delete = ToDoList.query.get(list_id)
    if list_to_delete.author == current_user:
        return render_template("confirm.html", list_=list_to_delete)
    return abort(403)


@app.route("/delete-list/<int:list_id>", methods=["GET", "POST"])
@login_required
def delete_list(list_id):
    """Deletes a list from the db if the current user is the author of the list."""
    list_to_delete = ToDoList.query.get(list_id)
    if list_to_delete.author == current_user:
        db.session.delete(list_to_delete)
        db.session.commit()
        return redirect(url_for("my_lists"))
    return abort(403)


@app.route("/guide")
def guide():
    """Renders the tutorial from the first list in the database. Page index 
    controls which element is considered 'active' in the navbar."""
    guide_list = ToDoList.query.get(1)
    return render_template("guide.html", page_index=2, list_=guide_list)


@app.route("/about")
def about():
    """Renders the about page. Page index controls which element is considered 
    'active' in the navbar."""
    return render_template("about.html", page_index=3)


@app.route("/contact")
def contact():
    """Renders the contact page. Page index controls which element is considered 
    'active' in the navbar."""
    return render_template("contact.html", page_index=4)


@app.route("/logout")
def logout():
    """Log out current user."""
    logout_user()
    return redirect(url_for("home"))


# DYNAMIC FOOTER
@app.context_processor
def inject_current_year():
    """Returns current year for date on the footer."""
    return {"current_year": date.today().year}


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

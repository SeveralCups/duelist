from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email


class EnlistForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()], render_kw={"autofocus": True})
    email = StringField("Email", validators=[Email(), DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[Email(), DataRequired()], render_kw={"autofocus": True})
    password = PasswordField("Password", validators=[DataRequired()])


class NewListForm(FlaskForm):
    name = StringField("List Name", validators=[DataRequired()], render_kw={"autofocus": True})

class AddItemForm(FlaskForm):
    content = StringField("New Item", validators=[DataRequired()], render_kw={"autofocus": True})

class EnlistHelpForm(FlaskForm):
    email = StringField("Email", validators=[Email(), DataRequired()])

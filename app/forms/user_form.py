import re
import sqlalchemy as sa

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    HiddenField,
)
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Email,
    EqualTo,
    Length,
)

from app.extensions import db
from app.models.user import User
from app.utils.validators import is_thapar_email
from app.models.app_setting import AppSetting

class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

    def validate_email(self, email):
        if not is_thapar_email(email.data):
            raise ValidationError("Only @thapar.edu email addresses are allowed.")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=64)]
    )

    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )

    hostel_number = StringField(
        "Hostel Number / Code",
        validators=[DataRequired(), Length(min=1, max=20)]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    password2 = PasswordField(
        "Repeat Password",
        validators=[DataRequired(), EqualTo("password")]
    )

    submit = SubmitField("Register")

    def validate_username(self, username):
        user = db.session.scalar(
            sa.select(User).where(User.username == username.data)
        )
        if user is not None:
            raise ValidationError("Please use a different username.")

    def validate_email(self, email):
        user = db.session.scalar(
            sa.select(User).where(User.email == email.data)
        )
        if user is not None:
            raise ValidationError("Please use a different email address.")

        if not is_thapar_email(email.data):
            raise ValidationError("Only @thapar.edu email addresses are allowed.")

    def validate_password(self, password):
        pwd = password.data

        if len(pwd) <= 6:
            raise ValidationError("Password must be more than 6 characters long.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd):
            raise ValidationError(
                "Password must contain at least one special character."
            )


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(
        "Thapar Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    submit = SubmitField("Request Password Reset")

    def validate_email(self, email):
        if not is_thapar_email(email.data):
            raise ValidationError("Only @thapar.edu email addresses are allowed.")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New Password",
        validators=[DataRequired()]
    )

    password2 = PasswordField(
        "Repeat New Password",
        validators=[DataRequired(), EqualTo("password")]
    )

    submit = SubmitField("Reset Password")

    def validate_password(self, password):
        pwd = password.data

        if len(pwd) <= 6:
            raise ValidationError("Password must be more than 6 characters long.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd):
            raise ValidationError(
                "Password must contain at least one special character."
            )


class EmailVerificationForm(FlaskForm):
    email = HiddenField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    otp = StringField(
        "OTP",
        validators=[DataRequired(), Length(min=6, max=6)]
    )
    submit = SubmitField("Verify Email")


class EditProfileForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=64)]
    )
    about_me = TextAreaField(
        "About Me",
        validators=[Length(min=0, max=140)]
    )
    submit = SubmitField("Submit")

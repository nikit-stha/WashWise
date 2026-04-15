import re
import sqlalchemy as sa

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    HiddenField,
)
from wtforms.validators import (
    ValidationError,
    AnyOf,
    DataRequired,
    Email,
    EqualTo,
    Length,
)

from app.extensions import db
from app.models.user import User
from app.utils.validators import is_thapar_email
from app.models.app_setting import AppSetting
from app.utils.hostels import HOSTEL_CHOICES, VALID_HOSTEL_CODES

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
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(min=3, max=64)]
    )

    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )

    hostel_number = SelectField(
        "Hostel",
        choices=(("", "Select your hostel"), *HOSTEL_CHOICES),
        validators=[
            DataRequired(message="Please select your hostel."),
            AnyOf(
                VALID_HOSTEL_CODES,
                message="Please choose a hostel from the list.",
            ),
        ],
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
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(min=3, max=64)]
    )
    about_me = TextAreaField(
        "About Me",
        validators=[Length(min=0, max=140)]
    )
    submit = SubmitField("Submit")

import re
import sqlalchemy as sa

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length

from app.extensions import db
from app.models.staff import Staff


class StaffLoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )
    registration_key = PasswordField(
        "Staff Registration Key",
        validators=[DataRequired(), Length(min=4, max=128)]
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

    def validate_registration_key(self, registration_key):
        expected_key = current_app.config.get("STAFF_REGISTRATION_KEY", "").strip()

        if not expected_key:
            raise ValidationError(
                "Staff login is currently unavailable. Contact an administrator."
            )

        if registration_key.data.strip() != expected_key:
            raise ValidationError("Invalid staff registration key.")


class StaffRegistrationForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(min=2, max=64)]
    )

    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=7)]
    )

    password2 = PasswordField(
        "Repeat Password",
        validators=[DataRequired(), EqualTo("password")]
    )

    registration_key = PasswordField(
        "Staff Registration Key",
        validators=[DataRequired(), Length(min=4, max=128)]
    )

    submit = SubmitField("Register")

    def validate_email(self, email):
        staff = db.session.scalar(
            sa.select(Staff).where(Staff.email == email.data)
        )
        if staff is not None:
            raise ValidationError("Please use a different email address.")

    def validate_password(self, password):
        pwd = password.data

        if len(pwd) <= 6:
            raise ValidationError("Password must be more than 6 characters long.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd):
            raise ValidationError(
                "Password must contain at least one special character."
            )

    def validate_registration_key(self, registration_key):
        expected_key = current_app.config.get("STAFF_REGISTRATION_KEY", "").strip()

        if not expected_key:
            raise ValidationError(
                "Staff registration is currently unavailable. Contact an administrator."
            )

        if registration_key.data.strip() != expected_key:
            raise ValidationError("Invalid staff registration key.")


class StaffResetPasswordRequestForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    submit = SubmitField("Request Password Reset")


class StaffResetPasswordForm(FlaskForm):
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


class StaffEmailVerificationForm(FlaskForm):
    email = HiddenField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    otp = StringField(
        "OTP",
        validators=[DataRequired(), Length(min=6, max=6)]
    )
    submit = SubmitField("Verify Email")

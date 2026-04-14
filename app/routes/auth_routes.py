from urllib.parse import urlsplit

from flask import current_app, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required, logout_user

from app.extensions import app
from app.forms.user_form import (
    LoginForm,
    RegistrationForm,
    ResetPasswordRequestForm,
    ResetPasswordForm,
    EmailVerificationForm,
)
from app.forms.staff_form import (
    StaffLoginForm,
    StaffRegistrationForm,
    StaffResetPasswordRequestForm,
    StaffResetPasswordForm,
    StaffEmailVerificationForm,
)
from app.models.user import User
from app.models.staff import Staff
from app.services.auth_service import (
    register_user,
    complete_user_registration,
    resend_pending_user_registration_otp,
    has_pending_user_registration,
    pending_user_registration_requires_verification,
    login_user_service,
    register_staff,
    complete_staff_registration,
    resend_pending_staff_registration_otp,
    has_pending_staff_registration,
    pending_staff_registration_requires_verification,
    login_staff_service,
    get_user_by_email,
    reset_user_password,
    get_user_from_reset_token,
    get_staff_by_email,
    reset_staff_password,
    get_staff_from_reset_token,
    issue_user_email_verification_otp,
    verify_user_email_otp,
    issue_staff_email_verification_otp,
    verify_staff_email_otp,
)
from app.services.email_service import (
    send_user_password_reset_email,
    send_staff_password_reset_email,
    send_user_email_verification_otp_email,
    send_staff_email_verification_otp_email,
)
from app.utils.email_utils import MailConfigurationError


def _send_email_safely(send_fn, *args):
    try:
        send_fn(*args)
    except MailConfigurationError as error:
        current_app.logger.warning("Email delivery skipped: %s", error)
        return False, str(error)
    except Exception:
        current_app.logger.exception("Email delivery failed.")
        return False, "Email delivery failed. Check your SMTP settings and try again."

    return True, None


@app.route("/")
def index():
    if current_user.is_authenticated:
        if isinstance(current_user, User):
            return redirect(url_for("user_dashboard"))
        if isinstance(current_user, Staff):
            return redirect(url_for("staff_dashboard"))

    return render_template("index.html")


# ------------------ USER AUTH ------------------ #
@app.route("/user/login", methods=["GET", "POST"])
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()

    if form.validate_on_submit():
        user, status, error = login_user_service(
            form.email.data,   # ✅ FIXED (was username)
            form.password.data,
            remember=form.remember_me.data,
        )

        if status == "verification_required" and user is not None:
            _, otp, otp_error = issue_user_email_verification_otp(user.email)
            if otp and not otp_error:
                email_sent, email_error = _send_email_safely(send_user_email_verification_otp_email, user, otp)
                if not email_sent:
                    flash(email_error, "danger")
                    return redirect(url_for("user_verify_email", email=user.email))

            flash("Verify your email with the OTP we sent before signing in.", "warning")
            return redirect(url_for("user_verify_email", email=user.email))

        if error:
            if pending_user_registration_requires_verification(form.email.data, form.password.data):
                pending_user, otp, otp_error = resend_pending_user_registration_otp(form.email.data)
                if otp and not otp_error:
                    email_sent, email_error = _send_email_safely(send_user_email_verification_otp_email, pending_user, otp)
                    if not email_sent:
                        flash(email_error, "danger")
                        return redirect(url_for("user_verify_email", email=form.email.data.strip().lower()))

                flash("Complete email verification before signing in.", "warning")
                return redirect(url_for("user_verify_email", email=form.email.data.strip().lower()))

            flash(error, "danger")
            return redirect(url_for("user_login"))

        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("index")

        flash("Logged in successfully.", "success")
        return redirect(next_page)

    return render_template("user_login.html", form=form)


@app.route("/user/verify-email", methods=["GET", "POST"])
def user_verify_email():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    email = request.args.get("email", "").strip().lower()
    if not email:
        flash("Verification email address is missing.", "danger")
        return redirect(url_for("user_register"))

    user = get_user_by_email(email)
    if user is not None and user.is_email_verified:
        flash("Your email is already verified. Please sign in.", "success")
        return redirect(url_for("user_login"))

    if user is None:
        if not has_pending_user_registration(email):
            flash("No pending verification found. Please register again.", "danger")
            return redirect(url_for("user_register"))

    form = EmailVerificationForm(email=email)

    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)
        if user is None:
            _, error = complete_user_registration(form.email.data, form.otp.data)
        else:
            _, error = verify_user_email_otp(form.email.data, form.otp.data)
        if error:
            flash(error, "danger")
            return redirect(url_for("user_verify_email", email=email))

        flash("Email verified successfully. You can now sign in.", "success")
        return redirect(url_for("user_login"))

    return render_template("verify_email.html", form=form, email=email, account_type="user")


@app.route("/user/resend-verification", methods=["POST"])
def resend_user_verification():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    email = request.form.get("email", "").strip().lower()
    user = get_user_by_email(email)
    if user is None:
        user, otp, error = resend_pending_user_registration_otp(email)
    else:
        user, otp, error = issue_user_email_verification_otp(email)

    if error:
        flash(error, "danger")
        return redirect(url_for("user_register"))

    email_sent, email_error = _send_email_safely(send_user_email_verification_otp_email, user, otp)
    if not email_sent:
        flash(email_error, "danger")
        return redirect(url_for("user_verify_email", email=email))

    flash("A new verification OTP has been sent to your email.", "info")
    return redirect(url_for("user_verify_email", email=email))


@app.route("/user/logout")
@login_required
def user_logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/user/register", methods=["GET", "POST"])
def user_register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegistrationForm()

    if form.validate_on_submit():
        user, otp, error = register_user(
            form.username.data,
            form.email.data,
            form.password.data,
            form.hostel_number.data,
        )

        if error:
            flash(error, "danger")
            return redirect(url_for("user_register"))

        email_sent, email_error = _send_email_safely(send_user_email_verification_otp_email, user, otp)
        if not email_sent:
            flash(f"Registration started, but {email_error}", "warning")
            return redirect(url_for("user_verify_email", email=user.email))

        flash("Enter the OTP sent to your email to finish creating your account.", "success")
        return redirect(url_for("user_verify_email", email=user.email))

    return render_template("user_register.html", form=form)


@app.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)

        if user is not None:
            email_sent, email_error = _send_email_safely(send_user_password_reset_email, user)
            if not email_sent:
                flash(email_error, "danger")
                return redirect(url_for("reset_password_request"))

        flash(
            "If that email exists, a reset link has been sent.",
            "info",
        )
        return redirect(url_for("user_login"))

    return render_template("reset_password_request.html", form=form)


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    user = get_user_from_reset_token(token)
    if user is None:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("reset_password_request"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        _, error = reset_user_password(token, form.password.data)

        if error:
            flash(error, "danger")
            return redirect(url_for("reset_password", token=token))

        flash("Password reset successful.", "success")
        return redirect(url_for("user_login"))

    return render_template("reset_password.html", form=form)


# ------------------ STAFF AUTH ------------------ #
@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = StaffLoginForm()

    if form.validate_on_submit():
        staff, status, error = login_staff_service(
            form.email.data,
            form.password.data,
            form.registration_key.data,
            remember=form.remember_me.data,
        )

        if status == "verification_required" and staff is not None:
            _, otp, otp_error = issue_staff_email_verification_otp(staff.email)
            if otp and not otp_error:
                email_sent, email_error = _send_email_safely(send_staff_email_verification_otp_email, staff, otp)
                if not email_sent:
                    flash(email_error, "danger")
                    return redirect(url_for("staff_verify_email", email=staff.email))

            flash("Verify your email with the OTP we sent before signing in.", "warning")
            return redirect(url_for("staff_verify_email", email=staff.email))

        if error:
            if pending_staff_registration_requires_verification(form.email.data, form.password.data):
                pending_staff, otp, otp_error = resend_pending_staff_registration_otp(form.email.data)
                if otp and not otp_error:
                    email_sent, email_error = _send_email_safely(send_staff_email_verification_otp_email, pending_staff, otp)
                    if not email_sent:
                        flash(email_error, "danger")
                        return redirect(url_for("staff_verify_email", email=form.email.data.strip().lower()))

                flash("Complete email verification before signing in.", "warning")
                return redirect(url_for("staff_verify_email", email=form.email.data.strip().lower()))

            flash(error, "danger")
            return redirect(url_for("staff_login"))

        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("index")

        flash("Staff login successful.", "success")
        return redirect(next_page)

    return render_template("staff_login.html", form=form)


@app.route("/staff/verify-email", methods=["GET", "POST"])
def staff_verify_email():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    email = request.args.get("email", "").strip().lower()
    if not email:
        flash("Verification email address is missing.", "danger")
        return redirect(url_for("staff_register"))

    staff = get_staff_by_email(email)
    if staff is not None and staff.is_email_verified:
        flash("Your email is already verified. Please sign in.", "success")
        return redirect(url_for("staff_login"))

    if staff is None:
        if not has_pending_staff_registration(email):
            flash("No pending staff verification found. Please register again.", "danger")
            return redirect(url_for("staff_register"))

    form = StaffEmailVerificationForm(email=email)

    if form.validate_on_submit():
        staff = get_staff_by_email(form.email.data)
        if staff is None:
            _, error = complete_staff_registration(form.email.data, form.otp.data)
        else:
            _, error = verify_staff_email_otp(form.email.data, form.otp.data)
        if error:
            flash(error, "danger")
            return redirect(url_for("staff_verify_email", email=email))

        flash("Email verified successfully. You can now sign in.", "success")
        return redirect(url_for("staff_login"))

    return render_template("staff_verify_email.html", form=form, email=email, account_type="staff")


@app.route("/staff/resend-verification", methods=["POST"])
def resend_staff_verification():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    email = request.form.get("email", "").strip().lower()
    staff = get_staff_by_email(email)
    if staff is None:
        staff, otp, error = resend_pending_staff_registration_otp(email)
    else:
        staff, otp, error = issue_staff_email_verification_otp(email)

    if error:
        flash(error, "danger")
        return redirect(url_for("staff_register"))

    email_sent, email_error = _send_email_safely(send_staff_email_verification_otp_email, staff, otp)
    if not email_sent:
        flash(email_error, "danger")
        return redirect(url_for("staff_verify_email", email=email))

    flash("A new verification OTP has been sent to your email.", "info")
    return redirect(url_for("staff_verify_email", email=email))


@app.route("/staff/register", methods=["GET", "POST"])
def staff_register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = StaffRegistrationForm()

    if form.validate_on_submit():
        staff, otp, error = register_staff(
            form.name.data,
            form.email.data,
            form.password.data,
            form.registration_key.data,
        )

        if error:
            flash(error, "danger")
            return redirect(url_for("staff_register"))

        email_sent, email_error = _send_email_safely(send_staff_email_verification_otp_email, staff, otp)
        if not email_sent:
            flash(f"Staff registration started, but {email_error}", "warning")
            return redirect(url_for("staff_verify_email", email=staff.email))

        flash("Enter the OTP sent to your email to finish creating your staff account.", "success")
        return redirect(url_for("staff_verify_email", email=staff.email))

    return render_template("staff_register.html", title="Staff Register", form=form)


@app.route("/staff/logout")
@login_required
def staff_logout():
    logout_user()
    flash("Staff logged out.", "info")
    return redirect(url_for("index"))


@app.route("/staff/reset_password_request", methods=["GET", "POST"])
def staff_reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = StaffResetPasswordRequestForm()

    if form.validate_on_submit():
        staff = get_staff_by_email(form.email.data)

        if staff is not None:
            email_sent, email_error = _send_email_safely(send_staff_password_reset_email, staff)
            if not email_sent:
                flash(email_error, "danger")
                return redirect(url_for("staff_reset_password_request"))

        flash(
            "If that staff email exists, a reset link has been sent.",
            "info",
        )
        return redirect(url_for("staff_login"))

    return render_template("staff_reset_password_request.html", form=form)


@app.route("/staff/reset_password/<token>", methods=["GET", "POST"])
def staff_reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    staff = get_staff_from_reset_token(token)
    if staff is None:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("staff_reset_password_request"))

    form = StaffResetPasswordForm()

    if form.validate_on_submit():
        _, error = reset_staff_password(token, form.password.data)

        if error:
            flash(error, "danger")
            return redirect(url_for("staff_reset_password", token=token))

        flash("Staff password reset successful.", "success")
        return redirect(url_for("staff_login"))

    return render_template("staff_reset_password.html", form=form)

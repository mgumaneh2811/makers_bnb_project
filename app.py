import os
from flask import Flask, request, redirect, render_template, flash, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from lib.forms import LoginForm
from lib.database_connection import get_flask_database_connection
from lib.user import User
from lib.user_repository import UserRepository
from dotenv import load_dotenv
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from lib.booking import Booking
from lib.booking_repository import BookingRepository
from datetime import datetime
from lib.space import Space
from lib.space_repository import SpaceRepository


# Create a new Flask app
app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')


# == Get Index Page ==

@app.route('/index', methods=['GET'])
def get_index():
    return render_template('index.html')

@app.route('/', methods=[ 'GET' ])
def get_home():
    if current_user.is_authenticated:
        return redirect('/spaces')
    else:
        return redirect('/index')
    

# == Manages User Sessions ==

@login_manager.user_loader
def load_user(user_id):
    user_repo = UserRepository(get_flask_database_connection(app))
    return user_repo.find(user_id)


# == Creates New User ==

@app.route('/users', methods=['POST'])
def post_users():
    connection = get_flask_database_connection(app)
    repository = UserRepository(connection)
    user_name = request.form['user_name']
    password = request.form['password']
    email = request.form['email']
    phone = request.form['phone']

    user = User(None, user_name, password, email, phone)
    repository.create(user)
    return redirect('/login')


# == List a Space Page ==

@app.route('/spaces/new', methods=['GET'])
def get_list_a_space():
    return render_template('list_a_space.html', user=current_user)

@app.route("/list_a_space")
def list_a_space():
    return render_template("list_a_space.html", user=current_user)


# == Login Page ==

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user_repo = UserRepository(get_flask_database_connection(app))
        user = user_repo.find_by_email(request.form["user_name"])
        if user is not None and user.password == request.form["password"]:
            login_user(user)
            return redirect('/spaces')
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html', title='Log In', form=form)


# == Logs User Out ==

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/login')


# == Create New Space ==

@app.route('/spaces/new', methods =['POST'])
def post_new_space():
    if 'space_name' not in request.form or 'spaces_description' not in request.form:
        return 'Please provide a name and description', 400
    connection = get_flask_database_connection(app)
    repository = SpaceRepository(connection)
    space = Space(None, request.form['space_name'], request.form['spaces_description'], request.form['price_per_night'], request.form['available_from_date'], request.form['available_to_date'], request.form['user_id'])
    repository.create(space)
    return redirect(url_for('list_a_space'))


# == View Requests - Current User ==

@app.route('/spaces/request/<space_id>', methods=['GET'])
@login_required
def get_request_space(space_id):
    connection = get_flask_database_connection(app)
    booking_repo = BookingRepository(connection)
    space_repo = SpaceRepository(connection)

    bookings = booking_repo.find_for_space(space_id)
    space = space_repo.find(space_id)

    return render_template('request_a_space.html', user = current_user, space = space, bookings = bookings)


# == Request a Space ==

@app.route('/spaces/request', methods=['POST'])
@login_required
def post_request_space():
    space_id = request.form['space_id']
    requested_date = datetime.strptime(request.form['requested_date'], '%Y-%m-%d').date()
    connection = get_flask_database_connection(app)

    booking_repo = BookingRepository(connection)   
    booking = Booking(None, request.form['user_id'], space_id, requested_date, 'Requested')
    booking_repo.create(booking)

    space_repo = SpaceRepository(connection)
    space = space_repo.find(space_id)

    requested_date_str = datetime.strftime(requested_date,"%d %B %Y")
    return render_template('space_requested.html', user = current_user, space=space, requested_date_str = requested_date_str )


# == View All Requests ==

@app.route('/requests', methods=['GET'])
@login_required
def get_requests():
    connection = get_flask_database_connection(app)
    booking_repo = BookingRepository(connection)

    bookings_made = booking_repo.find_for_user(current_user.id)
    bookings_made_with_details = []
    for booking in bookings_made:
        bookings_made_with_details.append(collate_booking_details(booking))

    bookings_received = booking_repo.find_for_users_spaces(current_user.id)
    bookings_received_with_details = []
    for booking in bookings_received:
        bookings_received_with_details.append(collate_booking_details(booking))

    return render_template('requests.html', user = current_user, bookings_made = bookings_made_with_details, bookings_received = bookings_received_with_details)

def collate_booking_details(booking):
    connection = get_flask_database_connection(app)
    spaces_repo = SpaceRepository(connection)
    user_repo = UserRepository(connection)

    space = spaces_repo.find(booking.space_id)
    user = user_repo.find(booking.user_id)
    booking_details = {
        'id': booking.id,
        'space_id': space.id,
        'space_name': space.space_name,
        'booking_date': booking.booking_date,
        'status': booking.status,
        'requesting_user_name': user.user_name
    }

    return booking_details


# == View Your Booking Requests ==

@app.route('/requests/<id>', methods=['GET'])
@login_required
def get_request(id):
    connection = get_flask_database_connection(app)
    booking_repo = BookingRepository(connection)
    user_repo = UserRepository(connection)
    space_repo = SpaceRepository(connection)

    booking = booking_repo.find(id)
    requesting_user = user_repo.find(booking.user_id)
    space = space_repo.find(booking.space_id)

    other_requests = booking_repo.find_for_space(booking.space_id)

    other_requests_with_details = []
    for request in other_requests:
        if request.id != booking.id:
            other_requests_with_details.append(collate_booking_details(request))

    if space.user_id == current_user.id:
        page_mode = 'approver'
    else:
        page_mode = ''

    return render_template('view_request.html', id=id, page_mode=page_mode, other_requests=other_requests_with_details, space=space, booking=booking, requesting_user=requesting_user)


# == Approve or Deny Requests ==

@app.route('/requests/<id>', methods=['POST'])
@login_required
def get_user_request_update(id):
    connection = get_flask_database_connection(app)
    booking_repo = BookingRepository(connection)
    space_repo = SpaceRepository(connection)

    booking = booking_repo.find(id)
    space = space_repo.find(booking.space_id)

    space_user_id = space.user_id

    action = request.form['action'] 

    if action == 'approve':
        new_status = "Booked"
    if action == 'deny':
        new_status = "Rejected"
    
    if action != None and space_user_id == current_user.id:
        booking_repo.update_status(id, new_status)
    
    return redirect("/requests")

# == Viewing All Spaces or Filtered Spaces ==


@app.route("/spaces", methods=['GET'])
def get_all_spaces():
    connection = get_flask_database_connection(app)
    repository = SpaceRepository(connection)
    all_spaces = repository.all()

    from_date = request.args.get("available_from_date")
    to_date = request.args.get("available_to_date")

    if from_date and to_date:
        filtered_spaces = [
            space for space in all_spaces
            if str(space.available_from_date) <= to_date and str(space.available_to_date) >= from_date
        ]
        return render_template("spaces.html", spaces=filtered_spaces, selected_from=from_date, selected_to=to_date)

    # Default: show everything with no filtering
    return render_template("spaces.html", spaces=all_spaces, selected_from="", selected_to="")



# == SERVER ==

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5001)))

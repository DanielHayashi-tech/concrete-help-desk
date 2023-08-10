import datetime
from flask import Flask, current_app, flash, redirect, render_template, request, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user
from flask_migrate import Migrate
import os
from sqlalchemy import desc
from sqlalchemy.orm import aliased
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Agents, user_id)


# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://' + os.environ.get('DB_USER') + ':' + os.environ.get(
    'DB_PASSWORD') + '@' + os.environ.get('DB_HOST') + ':' + os.environ.get('DB_PORT') + '/' + os.environ.get('DB_NAME')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Company(db.Model):
    CompanyID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CompanyName = db.Column(db.String(255), nullable=False)
    customers = db.relationship('Customers', backref='company', lazy=True)


class AgentStatuses(db.Model):
    StatusID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    StatusName = db.Column(db.String(255), nullable=False)
    agents = db.relationship('Agents', backref='status', lazy=True)


class CustomerStatuses(db.Model):
    StatusID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    StatusName = db.Column(db.String(255), nullable=False)
    customers = db.relationship('Customers', backref='status', lazy=True)


class EquipmentStatuses(db.Model):
    StatusID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    StatusName = db.Column(db.String(255), nullable=False)
    equipments = db.relationship('Equipment', backref='status', lazy=True)


class RentalStatuses(db.Model):
    StatusID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    StatusName = db.Column(db.String(255), nullable=False)
    rentals = db.relationship('Rentals', backref='status', lazy=True)


class VehicleStatuses(db.Model):
    StatusID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    StatusName = db.Column(db.String(255), nullable=False)
    vehicles = db.relationship('Vehicles', backref='status', lazy=True)


class Agents(UserMixin, db.Model):
    AgentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AgentName = db.Column(db.String(255))
    AgentPassword = db.Column(db.String(255))
    StatusID = db.Column(db.Integer, db.ForeignKey('agent_statuses.StatusID'))
    updated_rentals = db.relationship('Rentals', primaryjoin="Agents.AgentID==Rentals.UpdatedByAgentID", backref='updated_by_agent', lazy=True)


    def get_id(self):
        return str(self.AgentID)  # Convert AgentID to string

    @property
    def is_active(self):
        # Assuming a StatusID of 1 indicates an active user
        return self.StatusID == 1

    @property
    def is_authenticated(self):
        # All logged-in users are authenticated
        return True

    @property
    def is_anonymous(self):
        # All users in the system are not anonymous
        return False


class Customers(db.Model):
    CustomerID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    FirstName = db.Column(db.String(255))
    LastName = db.Column(db.String(255))
    Phone = db.Column(db.String(15))
    AltPhone = db.Column(db.String(15))
    Email = db.Column(db.String(255))
    Address = db.Column(db.String(255))
    City = db.Column(db.String(255))
    State = db.Column(db.String(255))
    Zip = db.Column(db.String(10))
    TDL = db.Column(db.String(20))
    TDLExpirationDate = db.Column(db.Date)
    InsuranceExpDate = db.Column(db.Date)
    LeaseAgreement = db.Column(db.Text)
    CustomerNote = db.Column(db.Text)
    StatusID = db.Column(db.Integer, db.ForeignKey(
        'customer_statuses.StatusID'))
    UpdatedByAgentID = db.Column(db.Integer, db.ForeignKey('agents.AgentID'))
    rentals = db.relationship('Rentals', backref='customer', lazy=True)
    vehicles = db.relationship('Vehicles', backref='customer', lazy=True)
    CompanyID = db.Column(db.Integer, db.ForeignKey('company.CompanyID'))


class Equipment(db.Model):
    EquipmentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    EquipmentType = db.Column(db.String(255))
    Condition = db.Column(db.String(255))
    StatusID = db.Column(db.Integer, db.ForeignKey(
        'equipment_statuses.StatusID'))
    UpdatedByAgentID = db.Column(db.Integer, db.ForeignKey('agents.AgentID'))
    rentals = db.relationship('Rentals', backref='equipment', lazy=True)


class Rentals(db.Model):
    RentalID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CustomerID = db.Column(db.Integer, db.ForeignKey('customers.CustomerID'))
    EquipmentID = db.Column(db.Integer, db.ForeignKey('equipment.EquipmentID'))
    RentalDate = db.Column(db.Date)
    ReturnDate = db.Column(db.Date)
    ReturnTime = db.Column(db.String(255))
    InternalNote = db.Column(db.Text)
    StatusID = db.Column(db.Integer, db.ForeignKey('rental_statuses.StatusID'))
    UpdatedByAgentID = db.Column(db.Integer, db.ForeignKey('agents.AgentID'))


class Vehicles(db.Model):
    VehicleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CustomerID = db.Column(db.Integer, db.ForeignKey('customers.CustomerID'))
    VehicleModel = db.Column(db.String(255))
    VehicleMake = db.Column(db.String(255))
    # Year is represented as a string of length 4 in Flask-SQLAlchemy
    VehicleYear = db.Column(db.String(4))
    LicensePlate = db.Column(db.String(20))
    StatusID = db.Column(db.Integer, db.ForeignKey(
        'vehicle_statuses.StatusID'))
    UpdatedByAgentID = db.Column(db.Integer, db.ForeignKey('agents.AgentID'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Query the database to find the agent
        agent = Agents.query.filter_by(AgentName=username).first()

        # If the agent exists and the password matches, log them in
        if agent and check_password_hash(agent.AgentPassword, password):
            login_user(agent)
            session['username'] = username  # update session
            flash('Logged in successfully.')
            return redirect(url_for('modals'))

        flash('Invalid username or password.')
        return redirect(url_for('login'))

    # If the request method is 'GET', serve the login page
    elif request.method == 'GET':
        return render_template('index.html')  # render 'login.html'


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('index.html')  # render the index page with no data

##############################################################################################################################################################################################################################
#                                                                            LOGIN                                                                                                                                          #
##############################################################################################################################################################################################################################


@app.route('/display', methods=['GET'])
def display_data():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    query = db.session.query(
        Customers.CustomerID,
        Customers.FirstName,
        Customers.LastName,
        Customers.Email,
        Customers.Address,
        Customers.Phone,
        Customers.AltPhone,
        Customers.TDL,
        Customers.TDLExpirationDate,
        Customers.InsuranceExpDate,
        Equipment.EquipmentType,
        Rentals.ReturnDate,
        Rentals.ReturnTime,
        Rentals.InternalNote,
        Customers.CustomerNote
    ).join(Rentals, Customers.CustomerID == Rentals.CustomerID
           ).join(Equipment, Rentals.EquipmentID == Equipment.EquipmentID
                  # Only select Customers with StatusID equals to 1 (Active customers)
                  ).filter(Customers.StatusID == 1
                           # Only select Equipment with StatusID equals to 1 (Active Equipment)
                           ).filter(Equipment.StatusID == 1
                                    # Only select Rentals with StatusID equals to 1 (Active Rental)
                                    ).filter(Rentals.StatusID == 1
                                             ).order_by(Customers.CustomerID.desc()).all()

    # Create a list of dictionaries to hold the data for each row
    data = []
    for row in query:
        item = {
            'CustomerID': row.CustomerID,
            'FirstName': row.FirstName,
            'LastName': row.LastName,
            'Email': row.Email,
            'Address': row.Address,
            'Phone': row.Phone,
            'AltPhone': row.AltPhone,
            'TDL': row.TDL,
            # adjust the format as necessary
            'TDLExpirationDate': row.TDLExpirationDate.strftime('%Y-%m-%d'),
            'InsuranceExpDate': row.InsuranceExpDate,
            'EquipmentType': row.EquipmentType,
            'ReturnDate': row.ReturnDate,
            'ReturnTime': row.ReturnTime,  # adjust the format as necessary
            'InternalNote': row.InternalNote,
            'CustomerNote': row.CustomerNote
        }
        data.append(item)

    return render_template('display.html', data=data)


##############################################################################################################################################################################################################################
#                                                                            DISPLAY                                                                                                                                          #
##############################################################################################################################################################################################################################

@app.route('/modals', methods=['GET'])
def modals():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    customers_query = db.session.query(
        Customers.CustomerID,
        Customers.FirstName,
        Customers.LastName,
        Customers.Email,
        Customers.Phone,
        Customers.AltPhone,
        Customers.Address,
        Customers.City,
        Customers.State,
        Customers.Zip,
        Customers.TDL,
        Customers.TDLExpirationDate,
        Customers.InsuranceExpDate,
        Customers.CustomerNote,
        CustomerStatuses.StatusName
    ).join(
        CustomerStatuses, CustomerStatuses.StatusID == Customers.StatusID
    ).order_by(Customers.CustomerID.desc()).all()

    customers_data = []
    for row in customers_query:
        item = {
            'CustomerID': row.CustomerID,
            'FirstName': row.FirstName,
            'LastName': row.LastName,
            'Email': row.Email,
            'Phone': row.Phone,
            'AltPhone': row.AltPhone,
            'Address': row.Address,
            'City': row.City,
            'State': row.State,
            'Zip': row.Zip,
            'TDL': row.TDL,
            'TDLExpirationDate': row.TDLExpirationDate,
            'InsuranceExpDate': row.InsuranceExpDate,
            'CustomerNote': row.CustomerNote,
            'StatusName': row.StatusName,  # Changed from StatusID to StatusName
        }
        customers_data.append(item)

    equipment_query = db.session.query(
        Equipment.EquipmentID,
        Equipment.EquipmentType,
        Equipment.Condition,
        Equipment.StatusID,
        EquipmentStatuses.StatusName,
    ).join(
        EquipmentStatuses, Equipment.StatusID == EquipmentStatuses.StatusID
    ).all()

    equipment_data = []
    for row in equipment_query:
        item = {
            'EquipmentID': row.EquipmentID,
            'EquipmentType': row.EquipmentType,
            'Condition': row.Condition,
            'StatusID': row.StatusID,
            'EquipmentStatusName': row.StatusName,
        }
        equipment_data.append(item)

    rental_query = db.session.query(
        Rentals.RentalID,
        Customers.CustomerID,
        Customers.FirstName,
        Customers.LastName,
        Equipment.EquipmentType,
        Equipment.StatusID.label('EquipmentStatusID'),
        Rentals.StatusID.label('RentalsStatusID'),
        Rentals.RentalDate,
        Rentals.ReturnDate,
        Rentals.ReturnTime,
        Equipment.EquipmentType,
        Rentals.InternalNote
    ).join(Customers, Customers.CustomerID == Rentals.CustomerID
           ).join(Equipment, Equipment.EquipmentID == Rentals.EquipmentID
                  # Only select Customers with StatusID equals to 2 (Active customers)
                  ).filter(Customers.StatusID == 2
                           # Only select Equipment with StatusID equals to 2 (Active Equipment)
                           ).filter(Equipment.StatusID == 2
                                    # Only select Rentals with StatusID equals to 2 (Active Rental)
                                    ).filter(Rentals.StatusID == 2
                                             ).order_by(Rentals.RentalID.desc()).all()

    rental_data = []
    for row in rental_query:
        item = {
            'RentalID': row.RentalID,
            'CustomerID': row.CustomerID,  # Including the CustomerID in the item
            'FirstName': row.FirstName,
            'LastName': row.LastName,
            'EquipmentType': row.EquipmentType,
            'EquipmentStatusID': row.EquipmentStatusID,
            'RentalDate': row.RentalDate,
            'ReturnDate': row.ReturnDate,
            'ReturnTime': row.ReturnTime,
            'InternalNote': row.InternalNote,
            'RentalsStatusID': row.RentalsStatusID,
        }
        print(rental_data)
        rental_data.append(item)

    vehicles_query = db.session.query(
        Vehicles.VehicleID,
        Customers.CustomerID,
        Vehicles.VehicleModel,
        Vehicles.VehicleMake,
        Vehicles.VehicleYear,
        Vehicles.LicensePlate,
        Vehicles.StatusID,
    ).join(Customers, Customers.CustomerID == Vehicles.CustomerID
           ).order_by(Vehicles.VehicleID.desc()).all()

    vehicles_data = []
    for row in vehicles_query:
        item = {
            'VehicleID': row.VehicleID,
            'CustomerID': row.CustomerID,
            'VehicleModel': row.VehicleModel,
            'VehicleMake': row.VehicleMake,
            'VehicleYear': row.VehicleYear,
            'LicensePlate': row.LicensePlate,
            'StatusID': row.StatusID
        }
        vehicles_data.append(item)

    return render_template('modals.html', customers_data=customers_data, equipment_data=equipment_data, rental_data=rental_data, vehicles_data=vehicles_data)

##############################################################################################################################################################################################################################
#                                                                            TAABLES                                                                                                                                          #
##############################################################################################################################################################################################################################


@app.route('/printedPage/<customer_id>')
def printable_page(customer_id):
    customer_id = int(customer_id)  # Convert to integer
    # This will return 404 if customer not found
    customer = Customers.query.get_or_404(customer_id)

    # We can get customer status name directly from the customer object due to defined relationship
    status_name = customer.status.StatusName

    # Fetch equipment type for this customer's rentals
    # We assume the customer has only one rental. If the customer can have multiple rentals,
    # this code needs to be modified to handle that
    rental = Rentals.query.filter_by(CustomerID=customer_id).first()
    if rental is not None:
        equipment_type = rental.equipment.EquipmentType
    else:
        equipment_type = None  # or some default value

    # Pass the data to the template
    return render_template('printedPage.html', row=customer, StatusName=status_name, EquipmentType=equipment_type)


##############################################################################################################################################################################################################################
#                                                                            Printed Page                                                                                                                                          #
##############################################################################################################################################################################################################################


@app.route('/update_customer/<int:id>', methods=['PUT'])
def update_customer(id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    # Get the customer from the database
    customer = Customers.query.get(id)

    if not customer:
        # If the customer was not found, return an error
        return jsonify({'error': 'Customer not found'}), 404

    # Get the updated data from the request
    data = request.get_json()

    # Update the customer data
    for key, value in data.items():
        setattr(customer, key, value)

    try:
        # Save the changes to the database
        db.session.commit()
        return jsonify({'message': 'Customer data updated successfully'})
    except Exception as e:
        db.session.rollback()  # Rollback the changes on error
        print(e)  # print the error to the console
        return jsonify({'error': 'An error occurred while updating customer data', 'details': str(e)}), 500


@app.route('/update_equipment/<int:id>', methods=['PUT'])
def update_equipment(id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    # Get the equipment from the database
    equipment = Equipment.query.get(id)

    if not equipment:
        # If the equipment was not found, return an error
        return jsonify({'error': 'equipment not found'}), 404

    # Get the updated data from the request
    data = request.get_json()

    # Update the equipment data
    for key, value in data.items():
        setattr(equipment, key, value)

    try:
        # Save the changes to the database
        db.session.commit()
        return jsonify({'message': 'equipment data updated successfully'})
    except Exception as e:
        db.session.rollback()  # Rollback the changes on error
        print(e)  # print the error to the console
        return jsonify({'error': 'An error occurred while updating equipment data', 'details': str(e)}), 500


@app.route('/update_rentals/<int:id>', methods=['PUT'])
def update_rentals(id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    # Get the rentals from the database
    rentals = Rentals.query.get(id)

    if not rentals:
        # If the rentals was not found, return an error
        return jsonify({'error': 'rentals not found'}), 404

    # Get the updated data from the request
    data = request.get_json()

    # Update the rentals data
    for key, value in data.items():
        setattr(rentals, key, value)

    try:
        # Save the changes to the database
        db.session.commit()
        return jsonify({'message': 'rentals data updated successfully'})
    except Exception as e:
        db.session.rollback()  # Rollback the changes on error
        print(e)  # print the error to the console
        return jsonify({'error': 'An error occurred while updating rentals data', 'details': str(e)}), 500


@app.route('/update_vehicles/<int:id>', methods=['PUT'])
def update_vehicles(id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    # Get the vehicles from the database
    vehicles = Vehicles.query.get(id)

    if not vehicles:
        # If the vehicles was not found, return an error
        return jsonify({'error': 'vehicles not found'}), 404

    # Get the updated data from the request
    data = request.get_json()

    # Update the vehicles data
    for key, value in data.items():
        setattr(vehicles, key, value)

    try:
        # Save the changes to the database
        db.session.commit()
        return jsonify({'message': 'vehicles data updated successfully'})
    except Exception as e:
        db.session.rollback()  # Rollback the changes on error
        print(e)  # print the error to the console
        return jsonify({'error': 'An error occurred while updating vehicles data', 'details': str(e)}), 500

##############################################################################################################################################################################################################################
#                                                                            UPDATE                                                                                                                                          #
##############################################################################################################################################################################################################################


@app.route('/availableEquipment', methods=['GET'])
def available_equipment():
    available_equipments = Equipment.query.filter_by(StatusID=2).all()
    result = [equipment.EquipmentType for equipment in available_equipments]
    return jsonify(result), 200


@app.route('/getEquipment_status_ids', methods=['GET'])
def get_status_ids_equipment():
    status_ids = EquipmentStatuses.query.all()
    return jsonify([{'id': status.StatusID, 'name': status.StatusName} for status in status_ids]), 200


@app.route('/getCustomer_status_ids', methods=['GET'])
def get_status_ids_customers():
    status_ids = CustomerStatuses.query.all()
    return jsonify([{'id': status.StatusID, 'name': status.StatusName} for status in status_ids]), 200


@app.route('/getRentals_status_ids', methods=['GET'])
def get_status_ids_rentals():
    status_ids = RentalStatuses.query.all()
    return jsonify([{'id': status.StatusID, 'name': status.StatusName} for status in status_ids]), 200


@app.route('/getVehicle_status_ids', methods=['GET'])
def get_status_ids_vehicles():
    status_ids = VehicleStatuses.query.all()
    return jsonify([{'id': status.StatusID, 'name': status.StatusName} for status in status_ids]), 200

##############################################################################################################################################################################################################################
#                                                                            GET                                                                                                                                          #
##############################################################################################################################################################################################################################


AVAILABLE_STATUS_ID = 2
ACTIVE_STATUS_ID = 1
RENTED_STATUS_ID = 1



@app.route('/create_customer', methods=['POST'])
def create_customer():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()

    required_fields = ['FirstName', 'LastName', 'Email', 'Address', 'City', 'State', 'Zip', 'Phone', 'AltPhone', 'TDL',
                       'TDLExpirationDate', 'InsuranceExpDate', 'CustomerNote', 'EquipmentType', 'RentalDate', 'ReturnDate', 'ReturnTime', 'InternalNote']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({'error': 'Missing required fields', 'fields': missing_fields}), 400

    equipment_type = data['EquipmentType']
    available_equipment = Equipment.query.filter_by(
    EquipmentType=equipment_type, StatusID=AVAILABLE_STATUS_ID).first()

    if not available_equipment:
        return jsonify({'error': 'No available equipment found for the given type'}), 404

    # Update the equipment's status to indicate it's rented or unavailable
    available_equipment.StatusID = RENTED_STATUS_ID
    db.session.add(available_equipment)

    # Create a new Customer instance
    new_customer = Customers(
        FirstName=data['FirstName'],
        LastName=data['LastName'],
        Email=data['Email'],
        Address=data['Address'],
        City=data['City'],
        State=data['State'],
        Zip=data['Zip'],
        Phone=data['Phone'],
        AltPhone=data['AltPhone'],
        TDL=data['TDL'],
        TDLExpirationDate=data['TDLExpirationDate'],
        InsuranceExpDate=data['InsuranceExpDate'],
        CustomerNote=data['CustomerNote'],
        StatusID=ACTIVE_STATUS_ID,
        UpdatedByAgentID=current_user.AgentID
    )
    db.session.add(new_customer)
    db.session.commit()  # Commit here to get the CustomerID

    # Create a new Rental instance linking the customer and equipment
    new_rental = Rentals(
        CustomerID=new_customer.CustomerID,
        RentalDate=data['RentalDate'],
        ReturnDate=data['ReturnDate'],
        ReturnTime=data['ReturnTime'],
        InternalNote=data['InternalNote'],
        StatusID=ACTIVE_STATUS_ID,
        EquipmentID=available_equipment.EquipmentID,
        UpdatedByAgentID=current_user.AgentID
    )
    db.session.add(new_rental)
    
    try:
        db.session.commit()
        return jsonify({'message': 'New customer and rental added successfully!', 'customer_id': new_customer.CustomerID}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"An error occurred: {str(e)}")  # Logging the error
        return jsonify({'error': 'An error occurred while creating new customer and rental', 'details': str(e)}), 500


@app.route('/create_rental', methods=['POST'])
def create_rental():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json()

    new_rental = Rentals(
        CustomerID=data['CustomerID'],
        EquipmentID=data['EquipmentID'],
        RentalDate=data['RentalDate'],
        ReturnDate=data['ReturnDate'],
        ReturnTime=data['ReturnTime'],
        InternalNote=data['InternalNote'],
        StatusID=data['StatusID']
    )
    db.session.add(new_rental)
    try:
        db.session.commit()
        return jsonify({'message': 'New customer added successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating new customer', 'details': str(e)}), 500


@app.route('/create_vehicle', methods=['POST'])
def create_vehicle():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json()

    new_vehicle = Vehicles(
        CustomerID=data['CustomerID'],
        VehicleModel=data['VehicleModel'],
        VehicleMake=data['VehicleMake'],
        VehicleYear=data['VehicleYear'],
        LicensePlate=data['LicensePlate'],
        StatusID=data['StatusID']
    )
    db.session.add(new_vehicle)
    try:
        db.session.commit()
        return jsonify({'message': 'New vehicle added successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating new vehicle', 'details': str(e)}), 500


##############################################################################################################################################################################################################################
#                                                                            CREATE                                                                                                                                          #
##############################################################################################################################################################################################################################

@app.route('/changeStatus', methods=['POST'])
def change_status():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    # Get the customer ID and status from the request data
    customer_id = request.form.get('customerId')
    status_string = request.form.get('status')

    # Convert the status from string to integer
    if status_string == "Inactive":
        status_id = 2
    elif status_string == "Active":
        status_id = 1
    else:
        return jsonify({'error': 'Invalid status'}), 400

    # Get the customer from the database
    customer = Customers.query.get(customer_id)

    if not customer:
        # If the customer was not found, return an error
        return jsonify({'error': 'Customer not found'}), 404

    # Update the status of the customer
    customer.StatusID = status_id

    # If the customer status is set to Inactive, update the status of the equipment to "Ready to use"
    if status_string == "Inactive":
        # Get all the rentals of the customer
        rentals = Rentals.query.filter_by(CustomerID=customer.CustomerID).all()

        for rental in rentals:
            # Get the equipment of the rental
            equipment = Equipment.query.get(rental.EquipmentID)

            if equipment:
                equipment.StatusID = 2  # Assume 2 means "Ready to use"

    try:
        # Save the changes to the database
        db.session.commit()
        return jsonify({'message': 'Customer and equipment status updated successfully'})
    except Exception as e:
        db.session.rollback()  # Rollback the changes on error
        print(e)  # print the error to the console
        return jsonify({'error': 'An error occurred while updating statuses', 'details': str(e)}), 500

##############################################################################################################################################################################################################################
#                                                                    INACTIVE BUTTON                                                                                                                                         #
##############################################################################################################################################################################################################################


if __name__ == '__main__':
    app.run(debug=True)

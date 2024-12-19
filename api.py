import json
import variables
from flask import Flask, request, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = variables.FLASK_SECRET_KEY

USER_DATA_FILE = "json/userdata.json"
def load_user_data():
    global USER_DATA
    try:
        with open(USER_DATA_FILE, 'r') as file:
            USER_DATA = json.load(file)
    except FileNotFoundError:
        USER_DATA = {}  # Default empty data
    return USER_DATA

load_user_data()

protected_fields = frozenset({"username", "userid", "date_logged", "perm_lvl", "email"})


def save_user_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(USER_DATA, f, indent=4)


@app.route('/home')
def home():
    load_user_data()
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Home</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Welcome to the Home Page</h1>

    <!-- Wrap the buttons inside this container -->
    <div class="home-btn-container">
        <div class="home-btn" data-href="/login?redirect=/home">Login</div>
        <div class="home-btn" data-href="/logout">Logout</div>
        <div class="home-btn" data-href="/userdata/dashboard">Dashboard</div>
    </div>

    <script>
        // Add a click event to all .home-btn elements
        const buttons = document.querySelectorAll('.home-btn');
        buttons.forEach(button => {
            button.addEventListener('click', function() {
                window.location.href = button.getAttribute('data-href');
            });
        });
    </script>
</body>
</html>

    '''


@app.route('/load')
def load_user_data_route():
    global USER_DATA
    # Only load data once when needed (i.e., the first time) or ensure it gets loaded outside of this route
    if not USER_DATA:  # If USER_DATA is empty, load it
        try:
            with open(USER_DATA_FILE, 'r') as file:
                USER_DATA = json.load(file)
        except FileNotFoundError:
            USER_DATA = {}  # Return empty dictionary if the file doesn't exist

    return jsonify(USER_DATA)


@app.route('/')
def blank():
    global USER_DATA
    load_user_data()
    return redirect(url_for('home'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    global USER_DATA
    load_user_data()
    redir = request.args.get('redirect', '/userdata/dashboard')
    if request.method == 'POST':
        email = request.form.get('email')
        userid = str(request.form.get('userid'))
        key = str(request.form.get('key'))

        user_data = USER_DATA.get(userid)
        if not user_data:
            return '''
                <p>Login Failed: UserID not found.</p>
                <a href="/login">Try Again</a>
            ''', 404

        if "key" not in user_data or user_data.get("key") is None:
            return '''
                <p>Login Denied: User is not authorized.</p>
                <a href="/login">Try Again</a>
            ''', 403

        if user_data.get("email") == email and user_data.get("key") == key:
            session['user'] = userid
            return redirect(redir)
        else:
            return '''
                <p>Login Failed: Invalid credentials.</p>
                <a href="/login">Try Again</a>
            ''', 401

    return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Login</title>
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body>
            <h1>Login</h1>
            <div class="login-div">
                <form class="login "method="post">
                    Email: <input type="email" name="email" required><br>
                    UserID: <input type="text" name="userid" required><br>
                    SecretKey: <input type="password" name="key" required><br>
                    <button type="submit">Login</button>
                </form>
            </div>
        </body>
        </html>
    '''


@app.route('/userdata/login', methods=['GET', 'POST'])
def userdata_login():
    # Get the arguments from the request
    args = request.args

    # Build a query string from the args
    query_string = '&'.join(f"{key}={value}" for key, value in args.items())
    query_string = query_string.removeprefix("&")

    # Redirect to '/login' with the query parameters
    return redirect(f"/login?{query_string}")


@app.route('/userdata/dashboard', methods=['GET', 'POST'])
def dashboard():
    global USER_DATA
    load_user_data()
    if 'user' not in session:
        return redirect("/login?redirect=/userdata/dashboard")

    userid = session['user']
    user_data = USER_DATA.get(userid, {})

    # User Data as a list with Edit and Remove buttons for each item
    user_data_html = ''
    for key, value in user_data.items():
        if key in protected_fields and not user_data.get("perm_lvl") == "4 (owner)":
            if user_data.get("perm_lvl") == "3 (admin)":
                user_data_html += f'''
                    <li>
                        <span>{key}: {value}</span>
                        <div class="btn-group">
                            <button class="edit-btn" onclick="openEditModal('{key}', '{value}')">Edit</button>
                        </div>
                    </li>
                    '''
            else:
                user_data_html += f'''
                    <li>
                        <span>{key}: {value}</span>
                        <div class="btn-group">
                            <button class="edit-btn">Protected</button>
                        </div>
                    </li>
                    '''
        else:
            if int(user_data.get("perm_lvl")[0]) > 1:
                user_data_html += f'''
                    <li>
                        <span>{key}: {value}</span>
                        <div class="btn-group">
                            <button class="edit-btn" onclick="openEditModal('{key}', '{value}')">Edit</button>
                            <button class="remove-btn" onclick="openRemoveModal('{key}')">-</button>
                        </div>
                    </li>
                '''
            else:
                user_data_html += f'''
                    <li>
                        <span>{key}: {value}</span>
                        <div class="btn-group">
                            <button class="edit-btn">You don't have permission</button>
                        </div>
                    </li>
                '''

    return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Dashboard</title>
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <h1>Welcome to your dashboard, {user_data.get("username", "User")}!</h1>
                <ul>
                    {user_data_html or "<li>No data available.</li>"}
                </ul>
                <button class="form-button" onclick="toggleAddForm()">+</button>
            </div>
            <a href="/logout">Logout</a>

            <!-- Edit Modal -->
            <div id="edit-modal" class="modal" style="display:none">
                <div class="modal-content">
                    <h2>Edit Data</h2>
                    <label for="edit-value">New Value:</label><br>
                    <input type="text" id="edit-value" name="value" required><br><br>
                    <button onclick="submitEditData()">Save Changes</button>
                    <button onclick="closeModal('edit')">Cancel</button>
                </div>
            </div>

            <!-- Add Modal -->
            <div id="add-modal" class="modal" style="display:none">
                <div class="modal-content">
                    <h2>Add Data</h2>
                    <label for="add-key">Key:</label><br>
                    <input type="text" id="add-key" name="key" required><br><br>
                    <label for="add-value">Value:</label><br>
                    <input type="text" id="add-value" name="value" required><br><br>
                    <button onclick="submitAddData()">Save Changes</button>
                    <button onclick="closeModal('add')">Cancel</button>
                </div>
            </div>

            <!-- Remove Modal -->
            <div id="remove-modal" class="modal" style="display:none">
                <div class="modal-content">
                    <h2>Are you sure you want to remove this data?</h2>
                    <button onclick="submitRemoveData()">Yes, Remove</button>
                    <button onclick="closeModal('remove')">Cancel</button>
                </div>
            </div>

            <script>
                var currentKeyToEdit = '';
                var currentKeyToRemove = '';

                function openEditModal(key, value) {{
                    document.getElementById('edit-value').value = value;
                    currentKeyToEdit = key;
                    document.getElementById('edit-modal').style.display = 'flex';
                }}

                function openRemoveModal(key) {{
                    currentKeyToRemove = key;
                    document.getElementById('remove-modal').style.display = 'flex';
                }}

                function closeModal(type) {{
                    if (type === 'edit') {{
                        document.getElementById('edit-modal').style.display = 'none';
                    }} else if (type === 'add') {{
                        document.getElementById('add-modal').style.display = 'none';
                    }} else {{
                        document.getElementById('remove-modal').style.display = 'none';
                    }}
                }}

                function submitEditData() {{
                    var newValue = document.getElementById('edit-value').value;
                    if (newValue) {{
                        fetch('/userdata/set', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ key: currentKeyToEdit, value: newValue }})
                        }})
                        .then(response => {{
                            if (response.ok) {{
                                location.reload();
                            }}
                        }});
                    }}
                }}

                function submitRemoveData() {{
                    fetch('/userdata/rm', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ key: currentKeyToRemove }})
                    }})
                    .then(response => {{
                        if (response.ok) {{
                            location.reload();
                        }}
                    }});
                }}

                function toggleAddForm() {{
                    var form = document.getElementById('add-modal');
                    form.style.display = (form.style.display === 'none' ? 'flex' : 'none');
                }}

                function submitAddData() {{
                    var key = document.getElementById('add-key').value;
                    var value = document.getElementById('add-value').value;
                    if (key && value) {{
                        fetch('/userdata/set', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ key: key, value: value }})
                        }})
                        .then(response => {{
                            if (response.ok) {{
                                location.reload(); // Reload to display the new data
                            }}
                        }});
                    }} else {{
                        alert("Both Key and Value are required!");
                    }}
                }}
            </script>
        </body>
        </html>
    '''


@app.route('/logout')
def logout():
    global USER_DATA
    load_user_data()
    session.pop('user', None)
    return redirect(url_for('home'))


@app.route('/userdata/get', methods=['GET'])
def get_user_data_dashboard():
    global USER_DATA
    load_user_data()
    if 'user' not in session:
        return redirect(url_for('login'))
    userid = session['user']
    key = request.args.get('key')

    if key:
        value = USER_DATA[userid].get(key, 'Key not found')
        return f'''
            <p>{key}: {value}</p>
            <a href="/userdata/dashboard">Back to Dashboard</a>
        '''
    else:
        user_data_html = ''.join(f"<li>{k}: {v}</li>" for k, v in USER_DATA[userid].items())
        return f'''
            <h1>User Data:</h1>
            <ul>{user_data_html or "<li>No data available.</li>"}</ul>
            <a href="/userdata/dashboard">Back to Dashboard</a>
        '''


@app.route('/userdata/set', methods=['POST'])
def set_user_data():
    global USER_DATA
    load_user_data()
    if 'user' not in session:
        return redirect(url_for('login'))
    userid = session['user']

    key = request.form.get('key')
    value = request.form.get('value')

    if not key or value is None:
        return '''
            <p>Error: Both key and value are required.</p>
            <a href="/userdata/dashboard">Back to Dashboard</a>
        '''

    USER_DATA[userid][key] = value
    save_user_data()

    return '''
        <p>Key and value set successfully!</p>
        <a href="/userdata/dashboard">Back to Dashboard</a>
    '''


@app.route('/userdata/rm', methods=['POST'])
def remove_user_data():
    global USER_DATA
    load_user_data()
    if 'user' not in session:
        return redirect(url_for('login'))
    userid = session['user']

    key = request.form.get('key')

    if not key:
        return '''
            <p>Error: Key is required for removal.</p>
            <a href="/userdata/dashboard">Back to Dashboard</a>
        '''

    if key in USER_DATA[userid]:
        del USER_DATA[userid][key]
        save_user_data()
        return '''
            <p>Key removed successfully!</p>
            <a href="/userdata/dashboard">Back to Dashboard</a>
        '''

    return '''
        <p>Error: Key not found.</p>
        <a href="/userdata/dashboard">Back to Dashboard</a>
    '''


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

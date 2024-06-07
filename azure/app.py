import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_session import Session
from dotenv import load_dotenv
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from openai import AzureOpenAI
from functools import wraps

load_dotenv()
app = Flask(__name__)

# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.urandom(24)
Session(app)

# Azure OpenAI and Azure Search connection details
AZURE_OPENAI_API_ENDPOINT = os.environ.get('ENDPOINT')
AZURE_OPENAI_API_KEY = os.environ.get('KEY')
AZURE_SEARCH_ENDPOINT = os.environ.get('SEARCH_ENDPOINT')
AZURE_SEARCH_INDEX = os.environ.get('SEARCH_INDEX')

# Azure SQL Database connection details
server = os.environ.get('SERVER')
database = os.environ.get('DATABASE')
username = os.environ.get('USER')
password = os.environ.get('PASSWORD')
driver = '{ODBC Driver 17 for SQL Server}'

# Construct the connection string
conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-02-01",
    azure_endpoint=AZURE_OPENAI_API_ENDPOINT
)

# Function to execute SQL queries
def execute_query(query, params=None, commit=False):
    conn = None
    cursor = None
    try:
        print(f"Executing query: {query} with params: {params}")  # Logging query
        conn = pyodbc.connect(conn_str)
        print(f"Connected to database: {conn_str}")  # Logging connection
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        print("Query executed successfully")  # Logging success

        if commit:
            conn.commit()  # Commit the transaction

        if cursor.description:
            columns = [column[0] for column in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            print(f"Query result: {result}")  # Logging result
            return result
        else:
            print("No data found")  # Logging no data
            return None
    except pyodbc.Error as e:
        print(f"Database error: {e}")  # Detailed logging
        raise
    finally:
        if cursor:
            cursor.close()  # Close cursor if it's open
        if conn:
            conn.close()    # Close connection if it's open


# Create the Users table if it doesn't exist
create_users_table_query = '''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' and xtype='U')
    CREATE TABLE Users (
        UserID INT IDENTITY(1,1) PRIMARY KEY,
        Username NVARCHAR(50) UNIQUE NOT NULL,
        Password NVARCHAR(255) NOT NULL
    )
'''
execute_query(create_users_table_query)

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        user_info = request.json
        username = user_info.get('username')
        password = user_info.get('password')
        hashed_password = generate_password_hash(password)

        # Insert user information into the Users table
        query = "INSERT INTO Users (Username, Password) VALUES (?, ?)"
        execute_query(query, (username, hashed_password), commit=True)  # Add commit=True
        return jsonify({'message': 'Registration successful'}), 200
    except pyodbc.IntegrityError:
        return jsonify({'message': 'Username already exists'}), 400
    except Exception as e:
        print(f"Error during registration: {e}")
        return jsonify({'message': 'Error during registration'}), 500


# Login a user
@app.route('/login', methods=['POST'])
def login():
    try:
        user_info = request.json
        username = user_info.get('username')
        password = user_info.get('password')

        print(f"Login attempt for user: {username}")  # Logging login attempt
        query = "SELECT * FROM Users WHERE Username = ?"
        user = execute_query(query, (username,))

        if user and check_password_hash(user[0]['Password'], password):
            session['username'] = username
            session['logged_in'] = True
            return jsonify({'message': 'Login successful'}), 200
        else:
            print(f"Login failed for user: {username}")  # Logging login failure
            return jsonify({'message': 'Invalid username or password'}), 401
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({'message': 'Error during login'}), 500

# Logout a user
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Protect the index route
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.json.get('message')

        # Generate the chat completion
        response = client.chat.completions.create(
            model="ChatAIEhb",  # Replace with your specific deployment name if needed
            messages=[
                {"role": "system", "content": "You are a helpful assistant who answers questions based on the provided dataset."},
                {"role": "user", "content": user_input}
            ],
            extra_body={
                "data_sources": [
                    {
                        "type": "azure_search",
                        "parameters": {
                            "endpoint": AZURE_SEARCH_ENDPOINT,
                            "index_name": AZURE_SEARCH_INDEX,
                            "authentication": {
                                "type": "api_key",
                                "key": os.environ.get('SEARCH_API_KEY')
                            }
                        }
                    }
                ]
            }
        )

        # Access the response data as attributes of the response object
        print("Response Data:", response)  # Debugging line

        if len(response.choices) > 0:
            ai_message = response.choices[0].message.content.strip()
        else:
            ai_message = "No response from AI."
        return jsonify({'message': ai_message})
    except Exception as e:
        print("Error during chat:", e)
        return jsonify({'message': 'Error during chat'}), 500

if __name__ == '__main__':
    app.run(debug=True)

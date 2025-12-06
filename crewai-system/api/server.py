import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_file, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import json
from datetime import datetime
from functools import wraps
import jwt
import bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.binary import Binary
import uuid
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
from datetime import timedelta

# Import agents
from agents import exim_agent, trials_agent, iqvia_agent, patent_agent, webintel_agent, internal_agent
from reports import report_generator
# Import the master agent from local_langchain instead of langchain
from local_langchain.master_agent import run_master_agent

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# SMTP configuration for OTP
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))

# Get port from environment or default to 4000
PORT = int(os.environ.get("PORT", 4000))

# JWT Secret
JWT_SECRET = os.environ.get("JWT_SECRET", "change_this_secret")

def generate_otp(length: int = 6) -> str:
    return ''.join(str(random.randint(0, 9)) for _ in range(length))

def send_otp_email(to_email: str, subject: str, otp: str):
    if not EMAIL_USER or not EMAIL_PASS:
        raise ValueError('EMAIL_USER/EMAIL_PASS not set in environment')
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    body = f"Your OTP is: {otp}\nIt expires in 10 minutes."
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())


def send_email(to_email: str, subject: str, body: str, html: bool = False):
    """Send a generic email using configured SMTP credentials."""
    if not EMAIL_USER or not EMAIL_PASS:
        raise ValueError('EMAIL_USER/EMAIL_PASS not set in environment')
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    if html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

def get_mongo_client():
    """Create and return a MongoDB client"""
    MONGO_URI = os.environ.get("MONGO_URI")
    if not MONGO_URI:
        raise ValueError("MONGO_URI not found in environment variables")
    return MongoClient(MONGO_URI)

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                parts = auth_header.split(' ')
                if len(parts) == 2 and parts[0] == 'Bearer':
                    token = parts[1]
            except:
                pass
        
        if not token:
            return jsonify({'msg': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user_id = data['id']
        except:
            return jsonify({'msg': 'Token is invalid!'}), 401
        
        return f(current_user_id, *args, **kwargs)
    
    return decorated

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "success",
        "message": "Pharma Mind Nexus API is running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """User signup endpoint"""
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', '')
        
        if not name or not email or not password:
            return jsonify({"msg": "Missing fields"}), 400
        
        client = get_mongo_client()
        db = client["pharma_hub"]
        users_collection = db["users"]
        
        # Check if user already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return jsonify({"msg": "Email already in use"}), 400
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user and generate signup OTP
        otp_code = generate_otp()
        otp_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

        user = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role,
            "verified": False,
            # notification preferences
            "email_notifications": True,
            "signup_otp": otp_code,
            "signup_otp_expires": otp_expires,
            "created_at": datetime.utcnow().isoformat()
        }

        result = users_collection.insert_one(user)
        user_id = str(result.inserted_id)

        # Send signup OTP
        try:
            send_otp_email(email, 'Verify your email (OTP)', otp_code)
        except Exception as mail_err:
            print(f"Failed to send signup OTP: {mail_err}")
            return jsonify({"msg": "User created, but OTP email failed. Contact support.", "user_id": user_id}), 200

        return jsonify({"msg": "Signup successful. OTP sent to your email.", "user_id": user_id}), 200
        
    except Exception as e:
        return jsonify({"msg": "Server error"}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    """Verify signup OTP and activate user"""
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        client = get_mongo_client()
        db = client['pharma_hub']
        users = db['users']
        user = users.find_one({"email": email})
        if not user:
            return jsonify({"msg": "User not found"}), 404
        if user.get('verified'):
            return jsonify({"msg": "Already verified"}), 200
        if user.get('signup_otp') != otp:
            return jsonify({"msg": "Invalid OTP"}), 400
        # Check expiry
        try:
            expires = datetime.fromisoformat(user.get('signup_otp_expires'))
            if datetime.utcnow() > expires:
                return jsonify({"msg": "OTP expired"}), 400
        except Exception:
            pass
        users.update_one({"email": email}, {"$set": {"verified": True}, "$unset": {"signup_otp": "", "signup_otp_expires": ""}})
        token = jwt.encode({'id': str(user['_id'])}, JWT_SECRET, algorithm="HS256")
        return jsonify({"msg": "Verification successful", "token": token}), 200
    except Exception:
        return jsonify({"msg": "Server error"}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/api/auth/signin', methods=['POST'])
def signin():
    """User signin endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"msg": "Missing fields"}), 400
        
        client = get_mongo_client()
        db = client["pharma_hub"]
        users_collection = db["users"]
        
        # Find user
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"msg": "Invalid credentials"}), 400
        
        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({"msg": "Invalid credentials"}), 400
        
        # Create JWT token
        token = jwt.encode({'id': str(user['_id'])}, JWT_SECRET, algorithm="HS256")
        
        # Return user data without password
        user_response = {
            "id": str(user['_id']),
            "name": user['name'],
            "email": user['email'],
            "role": user.get('role', '')
        }
        
        return jsonify({
            "user": user_response,
            "token": token
        }), 200
        
    except Exception as e:
        return jsonify({"msg": "Server error"}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_user(current_user_id):
    """Get current user profile"""
    try:
        client = get_mongo_client()
        db = client["pharma_hub"]
        users_collection = db["users"]
        
        # Find user
        user = users_collection.find_one({"_id": ObjectId(current_user_id)})
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        # Return user data without password, include preferences
        user_response = {
            "id": str(user['_id']),
            "name": user['name'],
            "email": user['email'],
            "role": user.get('role', ''),
            "email_notifications": bool(user.get('email_notifications', True))
        }
        
        return jsonify({"user": user_response}), 200
        
    except Exception as e:
        return jsonify({"msg": "Server error"}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/api/auth/me', methods=['PUT'])
@token_required
def update_user(current_user_id):
    """Update current user profile"""
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        role = data.get('role')
        
        client = get_mongo_client()
        db = client["pharma_hub"]
        users_collection = db["users"]
        
        # Find user
        user = users_collection.find_one({"_id": ObjectId(current_user_id)})
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        # Update fields
        update_data = {}
        if name:
            update_data['name'] = name
        if email:
            update_data['email'] = email
        if role is not None:
            update_data['role'] = role
        # Notification preferences
        if 'email_notifications' in data:
            try:
                update_data['email_notifications'] = bool(data.get('email_notifications'))
            except Exception:
                pass
            
        # Update user
        users_collection.update_one(
            {"_id": ObjectId(current_user_id)},
            {"$set": update_data}
        )
        
        # Return updated user data
        updated_user = users_collection.find_one({"_id": ObjectId(current_user_id)})
        user_response = {
            "id": str(updated_user['_id']),
            "name": updated_user['name'],
            "email": updated_user['email'],
            "role": updated_user.get('role', '')
        }
        
        return jsonify({"user": user_response}), 200
        
    except Exception as e:
        return jsonify({"msg": "Server error"}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/api/exim', methods=['GET'])
def get_exim_data():
    """Get EXIM trade data"""
    try:
        hs_code = request.args.get('hs_code')
        year_from = request.args.get('year_from')
        year_to = request.args.get('year_to')
        top_n = request.args.get('top_n', 10)
        
        # If no HS code provided, use a default one for pharmaceutical products
        if not hs_code:
            hs_code = "3004"  # Default HS code for pharmaceutical products
        
        data = exim_agent.get_trade_by_hs(
            hs_code=hs_code,
            year_from=year_from,
            year_to=year_to,
            top_n=int(top_n)
        )
        
        return jsonify({
            "query": f"EXIM data for HS code {hs_code}",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        # Return mock data as fallback
        try:
            mock_data = exim_agent.get_mock_trade_data(hs_code or "3004", int(top_n))
            return jsonify({
                "query": f"EXIM data for HS code {hs_code or '3004'}",
                "data": mock_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as mock_e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/trials', methods=['GET'])
def get_trials_data():
    """Get clinical trials data"""
    try:
        condition = request.args.get('condition')
        phase = request.args.get('phase')
        status = request.args.get('status')
        top_n = request.args.get('top_n', 10)
        
        # If no condition provided, use a default one
        if not condition:
            condition = "diabetes"  # Default condition
        
        data = trials_agent.search_trials(
            condition=condition,
            phase=phase,
            status=status,
            top_n=int(top_n)
        )
        
        return jsonify({
            "query": f"Clinical trials for {condition}",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        # Return mock data as fallback
        try:
            mock_data = trials_agent.get_mock_trials(condition or "diabetes", phase, status, int(top_n))
            return jsonify({
                "query": f"Clinical trials for {condition or 'diabetes'}",
                "data": mock_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as mock_e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/iqvia', methods=['GET'])
def get_iqvia_data():
    """Get IQVIA market data"""
    try:
        therapy_area = request.args.get('therapy_area')
        
        stats = iqvia_agent.get_market_stats(therapy_area=therapy_area)
        competitors = iqvia_agent.get_competitor_analysis(therapy_area=therapy_area)
        trends = iqvia_agent.get_therapy_trends(therapy_area=therapy_area)
        
        data = {
            "market_stats": stats,
            "competitors": competitors,
            "trends": trends
        }
        
        return jsonify({
            "query": f"IQVIA data for {therapy_area or 'general market'}",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/patents', methods=['GET'])
def get_patent_data():
    """Get patent data"""
    try:
        query = request.args.get('query')
        assignee = request.args.get('assignee')
        ipc_code = request.args.get('ipc_code')
        top_n = request.args.get('top_n', 10)
        
        # Use at least one search parameter
        if not query and not assignee and not ipc_code:
            # For gene therapy query, provide a default search
            if request.args.get('query', '').lower() == 'find recent patents related to gene therapy':
                query = 'gene therapy'
            else:
                query = "pharmaceutical"  # Default search term
        
        data = patent_agent.search_patents(
            query=query or "",
            assignee=assignee,
            ipc_code=ipc_code,
            top_n=int(top_n)
        )
        
        return jsonify({
            "query": f"Patent search for {query or assignee or ipc_code}",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        # Even if there's an exception, try to return mock data
        try:
            mock_data = patent_agent.get_mock_patent_data(query or "gene therapy", int(top_n))
            return jsonify({
                "query": f"Patent search for {query or assignee or ipc_code}",
                "data": mock_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as mock_e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/web-intel', methods=['GET'])
def get_web_intel_data():
    """Get web intelligence data"""
    try:
        query = request.args.get('query')
        num_results = request.args.get('num_results', 5)
        
        if not query:
            return jsonify({"error": "query parameter is required"}), 400
        
        data = webintel_agent.search_web(
            query=query,
            num_results=int(num_results)
        )
        
        return jsonify({
            "query": f"Web search for {query}",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/internal-docs', methods=['GET'])
def get_internal_docs():
    """Get internal documents"""
    try:
        query = request.args.get('query')
        top_n = request.args.get('top_n', 5)
        
        if not query:
            return jsonify({"error": "query parameter is required"}), 400
        
        data = internal_agent.search_internal_documents(
            query=query,
            top_n=int(top_n)
        )
        
        return jsonify({
            "query": f"Internal documents for {query}",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/master-agent', methods=['POST'])
def run_master_agent_endpoint():
    """Run the master agent with a query"""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({"error": "query parameter is required"}), 400
        
        # Run master agent
        response = run_master_agent(query)
        
        return jsonify({
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """Generate a report from collected data and store it in MongoDB"""
    client = None
    try:
        data = request.get_json()
        query = data.get('query')
        results = data.get('results')
        report_type = data.get('type', 'text')  # text, pdf, or excel
        user_id = data.get('user_id')  # Optional user ID
        
        print(f"Generating report: query={query}, type={report_type}, user_id={user_id}")
        
        # If results are not provided, fetch them server-side
        if not results:
            if not query:
                return jsonify({"error": "query is required"}), 400
            try:
                print("No results provided. Fetching data from agents...")
                # Build results from available agent endpoints
                exim = exim_agent.get_trade_by_hs(hs_code="3004", year_from=None, year_to=None, top_n=10)
                trials = trials_agent.search_trials(condition=query or "diabetes", phase=None, status=None, top_n=10)
                patents = patent_agent.search_patents(query=query, assignee=None, ipc_code=None, top_n=10)
                webintel = webintel_agent.search_web(query=query, num_results=5)
                internal_docs = internal_agent.search_internal_documents(query=query, top_n=5)
                iqvia_stats = iqvia_agent.get_market_stats(therapy_area=query)
                iqvia_comp = iqvia_agent.get_competitor_analysis(therapy_area=query)
                iqvia_trends = iqvia_agent.get_therapy_trends(therapy_area=query)

                results = {
                    "EXIM Trade Data": exim or [],
                    "Clinical Trials": trials or [],
                    "Patents": patents or [],
                    "Web Intel": webintel or [],
                    "Internal Docs": internal_docs or [],
                    "IQVIA": {
                        "market_stats": iqvia_stats or {},
                        "competitors": iqvia_comp or [],
                        "trends": iqvia_trends or []
                    }
                }
                print("Server-side results assembled.")
            except Exception as fetch_error:
                print(f"Error fetching server-side results: {fetch_error}")
                return jsonify({"error": "Failed to fetch results for report generation"}), 500
        
        # Filter out empty sections
        filtered_results = {k: v for k, v in results.items() if v}
        print(f"Filtered results keys: {list(filtered_results.keys())}")
        
        # Generate report
        filepath = None
        summary = None
        if report_type == 'pdf':
            filepath = report_generator.generate_pdf_report(query, filtered_results)
            print(f"PDF report generated: {filepath}")
            # Also generate Excel alongside PDF for convenience
            try:
                excel_path = report_generator.generate_excel_report(query, filtered_results)
                print(f"Excel report also generated: {excel_path}")
            except Exception as excel_err:
                print(f"Failed to generate parallel Excel: {excel_err}")
        elif report_type == 'excel':
            filepath = report_generator.generate_excel_report(query, filtered_results)
            print(f"Excel report generated: {filepath}")
        elif report_type == 'text':
            summary = report_generator.generate_text_summary(query, filtered_results)
            print(f"Text summary generated: {len(summary) if summary else 0} characters")
        else:
            return jsonify({"error": "Invalid report type. Use 'pdf', 'excel', or 'text'"}), 400
            
        # Store report in MongoDB
        print("Storing report in MongoDB...")
        client = get_mongo_client()
        db = client["pharma_hub"]
        reports_collection = db["reports"]
        
        # Create report record
        report_id = str(uuid.uuid4())
        report_record = {
            "report_id": report_id,
            "query": query,
            "report_type": report_type,
            "file_path": filepath if report_type in ['pdf', 'excel'] else None,
            "generated_at": datetime.now().isoformat(),
            "generated_by": user_id,
            "downloads": 0,
            "metadata": {
                "sections": list(filtered_results.keys()),
                "data_points": sum(len(v) if isinstance(v, list) else 1 for v in filtered_results.values())
            }
        }
        print(f"Report record prepared: {report_record}")
        
        # For PDF and Excel reports, store the binary data
        if report_type in ['pdf', 'excel'] and filepath:
            try:
                print(f"Reading file data from: {filepath}")
                with open(filepath, 'rb') as f:
                    binary_data = f.read()
                report_record["file_data"] = Binary(binary_data)
                print(f"Binary data read: {len(binary_data)} bytes")
            except Exception as file_error:
                print(f"Warning: Could not read file data: {file_error}")
                import traceback
                traceback.print_exc()
        
        # For text reports, store the summary
        if report_type == 'text' and summary:
            report_record["text_summary"] = summary
            
        # Insert report record into database
        print("Inserting report record into database...")
        result = reports_collection.insert_one(report_record)
        print(f"Report record inserted with ID: {result.inserted_id}")

        # Check Authorization header for user token to optionally send email notification
        try:
            auth_header = request.headers.get('Authorization', '')
            token = None
            if auth_header:
                parts = auth_header.split(' ')
                if len(parts) == 2 and parts[0] == 'Bearer':
                    token = parts[1]
            if token:
                try:
                    decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                    current_user_id = decoded.get('id')
                except Exception:
                    current_user_id = None
            else:
                current_user_id = None

            if current_user_id:
                try:
                    users_collection = db['users']
                    user = users_collection.find_one({"_id": ObjectId(current_user_id)})
                    if user and bool(user.get('email_notifications', True)):
                        user_email = user.get('email')
                        if user_email:
                            # Prepare a professional email notifying about report download
                            subject = 'Your Pharma Mind Nexus report is ready'
                            report_url = None
                            try:
                                # If the report was stored, provide a link to retrieve it
                                report_url = f"{request.host_url.rstrip('/')}/api/reports/{report_id}"
                            except Exception:
                                report_url = None
                            body_html = f"<p>Dear {user.get('name', '')},</p>\n"
                            body_html += f"<p>Your requested report (<strong>{report_record.get('query')}</strong>) has been generated on {report_record.get('generated_at')}. "
                            if report_url:
                                body_html += f"You can download it here: <a href='{report_url}'>Download Report</a>."
                            body_html += "</p>\n"
                            body_html += "<p>If you did not request this report or have any questions, please contact our support team.</p>\n"
                            body_html += "<p>Regards,<br/>Pharma Mind Nexus Team</p>"
                            try:
                                send_email(user_email, subject, body_html, html=True)
                                print(f"Notification email sent to {user_email}")
                            except Exception as mail_err:
                                print(f"Failed to send report notification to {user_email}: {mail_err}")
                except Exception as e:
                    print(f"Error while attempting to notify user: {e}")
        except Exception:
            pass

        # If we generated a parallel Excel, insert a separate record for it
        if report_type == 'pdf' and 'excel_path' in locals() and excel_path:
            try:
                excel_record = {**report_record}
                excel_record['report_id'] = str(uuid.uuid4())
                excel_record['report_type'] = 'excel'
                excel_record['file_path'] = excel_path
                if os.path.exists(excel_path):
                    with open(excel_path, 'rb') as ef:
                        excel_record['file_data'] = Binary(ef.read())
                reports_collection.insert_one(excel_record)
                print(f"Parallel Excel record inserted: {excel_record['report_id']}")
            except Exception as er:
                print(f"Failed to store parallel Excel record: {er}")
        
        # Return appropriate response
        print("Returning response...")
        if report_type in ['pdf', 'excel'] and filepath:
            # For file reports, return the report id and a download URL; frontend should call /api/reports/<report_id>/download
            download_url = f"/api/reports/{report_id}/download"
            return jsonify({"report_id": report_id, "download_url": download_url}), 200
        elif report_type == 'text' and summary:
            response = jsonify({
                "query": query,
                "summary": summary,
                "report_id": report_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            response = jsonify({"error": "Invalid report type or missing data"}), 400

        return response
            
    except Exception as e:
        print(f"Error generating report: {str(e)}")  # Log the error for debugging
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500
    finally:
        # Close MongoDB connection
        if client:
            try:
                client.close()
                print("MongoDB connection closed")
            except Exception as close_error:
                print(f"Error closing MongoDB connection: {close_error}")

@app.route('/api/reports', methods=['GET'])
def list_reports():
    """List all stored reports"""
    try:
        client = get_mongo_client()
        db = client["pharma_hub"]
        reports_collection = db["reports"]
        
        # Find all reports
        reports = list(reports_collection.find({}, {
            "report_id": 1, 
            "query": 1, 
            "report_type": 1, 
            "generated_at": 1, 
            "generated_by": 1, 
            "metadata": 1,
            "_id": 0
        }))
        
        # Fetch total downloads metric if available
        metrics_collection = db["metrics"]
        metrics_doc = metrics_collection.find_one({"_id": "downloads"})
        downloads_total = int(metrics_doc.get('count', 0)) if metrics_doc else 0

        # Close MongoDB connection
        client.close()

        # Return reports list with counts and downloads total
        total = len(reports)
        pdf_count = sum(1 for r in reports if r.get('report_type') == 'pdf')
        excel_count = sum(1 for r in reports if r.get('report_type') == 'excel')
        text_count = sum(1 for r in reports if r.get('report_type') == 'text')
        return jsonify({
            "reports": reports,
            "counts": {
                "total": total,
                "pdf": pdf_count,
                "excel": excel_count,
                "text": text_count
            },
            "downloads_total": downloads_total
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    """Retrieve a stored report by ID"""
    try:
        client = get_mongo_client()
        db = client["pharma_hub"]
        reports_collection = db["reports"]
        
        # Find report
        report = reports_collection.find_one({"report_id": report_id})
        if not report:
            return jsonify({"error": "Report not found"}), 404
        
        # Close MongoDB connection
        client.close()
        
        # Return report metadata
        return jsonify({
            "report_id": report["report_id"],
            "query": report["query"],
            "report_type": report["report_type"],
            "generated_at": report["generated_at"],
            "generated_by": report.get("generated_by"),
            "metadata": report.get("metadata")
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/reports/<report_id>/download', methods=['GET'])
def download_report(report_id):
    """Stream a stored report file, increment download metric, and delete report record."""
    client = None
    try:
        client = get_mongo_client()
        db = client["pharma_hub"]
        reports_collection = db["reports"]

        report = reports_collection.find_one({"report_id": report_id})
        if not report:
            return jsonify({"error": "Report not found"}), 404

        # Try to get file bytes
        file_bytes = None
        download_name = None
        if report.get('file_data'):
            try:
                file_bytes = bytes(report['file_data'])
                download_name = os.path.basename(report.get('file_path') or f"report_{report_id}")
            except Exception as e:
                print(f"Failed to read file_data for report {report_id}: {e}")
        elif report.get('file_path') and os.path.exists(report['file_path']):
            try:
                with open(report['file_path'], 'rb') as f:
                    file_bytes = f.read()
                download_name = os.path.basename(report.get('file_path'))
            except Exception as e:
                print(f"Failed to read file at path for report {report_id}: {e}")

        if not file_bytes:
            return jsonify({"error": "Report file not available"}), 404

        # Increment global downloads metric
        try:
            metrics_collection = db.get_collection('metrics')
            metrics_collection.update_one({"_id": "downloads"}, {"$inc": {"count": 1}}, upsert=True)
        except Exception as me:
            print(f"Failed to increment downloads metric: {me}")

        # Delete the report record
        try:
            reports_collection.delete_one({"report_id": report_id})
        except Exception as de:
            print(f"Failed to delete report {report_id}: {de}")

        # Stream the file back
        return send_file(io.BytesIO(file_bytes), as_attachment=True, download_name=download_name)

    except Exception as e:
        print(f"Error during report download: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass


@app.route('/api/reports/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete a stored report by ID."""
    client = None
    try:
        client = get_mongo_client()
        db = client["pharma_hub"]
        reports_collection = db["reports"]

        report = reports_collection.find_one({"report_id": report_id})
        if not report:
            return jsonify({"error": "Report not found"}), 404

        # Remove file on disk if exists
        try:
            if report.get('file_path') and os.path.exists(report['file_path']):
                try:
                    os.remove(report['file_path'])
                except Exception as e:
                    print(f"Failed to remove file for report {report_id}: {e}")
        except Exception:
            pass

        reports_collection.delete_one({"report_id": report_id})
        return jsonify({"msg": "Report deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass

@app.route('/api/reports/stats', methods=['GET'])
def report_stats():
    """Return counts of reports by type for dashboard counters"""
    try:
        client = get_mongo_client()
        db = client["pharma_hub"]
        reports_collection = db["reports"]

        pipeline = [
            {"$group": {"_id": "$report_type", "count": {"$sum": 1}}}
        ]
        agg = list(reports_collection.aggregate(pipeline))
        counts = {item['_id']: item['count'] for item in agg}
        total = sum(counts.values())
        return jsonify({
            "total": total,
            "pdf": counts.get('pdf', 0),
            "excel": counts.get('excel', 0),
            "text": counts.get('text', 0)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'client' in locals():
            try:
                client.close()
            except:
                pass

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Send reset OTP to user's email"""
    try:
        data = request.get_json()
        email = data.get('email')
        client = get_mongo_client()
        db = client['pharma_hub']
        users = db['users']
        user = users.find_one({"email": email})
        if not user:
            return jsonify({"msg": "Email not found"}), 404
        otp_code = generate_otp()
        otp_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        users.update_one({"email": email}, {"$set": {"reset_otp": otp_code, "reset_otp_expires": otp_expires}})
        try:
            send_otp_email(email, 'Password Reset OTP', otp_code)
        except Exception as mail_err:
            print(f"Failed to send reset OTP: {mail_err}")
            return jsonify({"msg": "OTP set but email failed. Contact support."}), 200
        return jsonify({"msg": "Reset OTP sent to your email"}), 200
    except Exception:
        return jsonify({"msg": "Server error"}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password using OTP"""
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        new_password = data.get('password')
        client = get_mongo_client()
        db = client['pharma_hub']
        users = db['users']
        user = users.find_one({"email": email})
        if not user:
            return jsonify({"msg": "User not found"}), 404
        if user.get('reset_otp') != otp:
            return jsonify({"msg": "Invalid OTP"}), 400
        try:
            expires = datetime.fromisoformat(user.get('reset_otp_expires'))
            if datetime.utcnow() > expires:
                return jsonify({"msg": "OTP expired"}), 400
        except Exception:
            pass
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        users.update_one({"email": email}, {"$set": {"password": hashed_password}, "$unset": {"reset_otp": "", "reset_otp_expires": ""}})
        return jsonify({"msg": "Password updated successfully"}), 200
    except Exception:
        return jsonify({"msg": "Server error"}), 500

if __name__ == '__main__':
    print(f"Starting Pharma Mind Nexus API server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
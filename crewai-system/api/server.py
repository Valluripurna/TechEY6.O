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
from agents.knowledge_agent import KnowledgeAgent
from agents.medical_reasoner import MedicalReasoner
from reports import report_generator
# Import the master agent from local_langchain instead of langchain
from local_langchain.master_agent import run_master_agent
from vector.pinecone_client import PineconeClient
from utils import generate_response, DOCUMENT_FIRST_SYSTEM_PROMPT

# Initialize agents
pinecone_client = PineconeClient()
knowledge_agent = KnowledgeAgent(pinecone_client)
medical_reasoner = MedicalReasoner()

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
CORS(app)  # Enable CORS for all routes

# Set max content length for form data specifically
app.config['MAX_FORM_MEMORY_SIZE'] = 16 * 1024 * 1024  # 16MB



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
        print(f"Signup request data: {data}")  # Debug log
        
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', '')
        
        # Validate required fields
        if not name or not email or not password:
            missing_fields = []
            if not name:
                missing_fields.append('name')
            if not email:
                missing_fields.append('email')
            if not password:
                missing_fields.append('password')
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            print(f"Signup validation error: {error_msg}")
            return jsonify({"msg": error_msg}), 400
        
        # Validate email format
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            error_msg = "Invalid email format"
            print(f"Signup validation error: {error_msg}")
            return jsonify({"msg": error_msg}), 400
        
        # Validate password strength
        if len(password) < 6:
            error_msg = "Password must be at least 6 characters long"
            print(f"Signup validation error: {error_msg}")
            return jsonify({"msg": error_msg}), 400
        
        client = get_mongo_client()
        db = client["pharma_hub"]
        users_collection = db["users"]
        
        # Check if user already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            error_msg = "Email already in use"
            print(f"Signup validation error: {error_msg}")
            return jsonify({"msg": error_msg}), 400
        
        # Generate OTP for email verification
        signup_otp = generate_otp()
        otp_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_data = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role,
            "verified": False,
            "signup_otp": signup_otp,
            "signup_otp_expires": otp_expires,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Send signup OTP (but don't fail signup if email fails)
        email_success = False
        try:
            send_otp_email(email, 'Verify your email (OTP)', signup_otp)
            email_success = True
            print(f"Signup OTP email sent successfully to {email}")
        except Exception as mail_err:
            error_msg = f"Failed to send signup OTP email: {str(mail_err)}"
            print(f"Signup email error: {error_msg}")
            # We don't return an error here - we still want to allow signup even if email fails
        
        # Return success response
        if email_success:
            success_msg = "Signup successful. OTP sent to your email."
            return jsonify({"msg": success_msg, "user_id": user_id}), 200
        else:
            success_msg = "Signup successful. Email verification temporarily unavailable."
            # Update user to indicate verification is not needed
            users_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": {"verification_needed": False}}
            )
            return jsonify({"msg": success_msg, "user_id": user_id}), 200
        
    except Exception as e:
        error_msg = f"Server error during signup: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
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
            
        # Check if account doesn't require verification (was created when email was down)
        if user.get('verification_needed') == False:
            # Mark as verified and generate token
            users.update_one({"email": email}, {"$set": {"verified": True}})
            token = jwt.encode({'id': str(user['_id'])}, JWT_SECRET, algorithm="HS256")
            return jsonify({"msg": "Verification successful", "token": token}), 200
            
        # Normal verification flow
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
        
        # Return user data without password
        user_response = {
            "id": str(user['_id']),
            "name": user['name'],
            "email": user['email'],
            "role": user.get('role', '')
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
            # Prefer streaming from DB if binary was captured; fallback to file path
            try:
                if 'file_data' in report_record:
                    data_bytes = bytes(report_record['file_data'])
                    download_name = os.path.basename(filepath)
                    return send_file(io.BytesIO(data_bytes), as_attachment=True, download_name=download_name)
            except Exception as stream_err:
                print(f"Stream from DB failed, falling back to file path: {stream_err}")
            # Fallback to sending the file by path
            return send_file(filepath, as_attachment=True)
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
        
        # Close MongoDB connection
        client.close()
        
        # Return reports list with counts
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
            }
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
    """Download a stored report by ID"""
    client = None
    try:
        client = get_mongo_client()
        db = client["pharma_hub"]
        reports_collection = db["reports"]
        
        report = reports_collection.find_one({"report_id": report_id})
        
        if not report:
            return jsonify({"error": "Report not found"}), 404
            
        if "file_data" not in report:
            return jsonify({"error": "No file data available for this report"}), 404
            
        file_data = report["file_data"]
        report_type = report["report_type"]
        query = report["query"]
        
        filename = f"{query.replace(' ', '_')}_{report_id}.{report_type}"

        # Increment download counters
        try:
            # Per-report download count
            reports_collection.update_one({"report_id": report_id}, {"$inc": {"download_count": 1}})
            # Global counters
            stats_collection = db.get_collection("stats")
            stats_collection.update_one(
                {"_id": "downloads"},
                {"$inc": {f"{report_type}_downloads": 1, "total_downloads": 1}},
                upsert=True
            )
        except Exception as cnt_err:
            print(f"Failed to increment download counters: {cnt_err}")
        
        return send_file(
            io.BytesIO(bytes(file_data)),
            mimetype=f"application/{report_type}",
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error downloading report: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to download report: {str(e)}"}), 500
    finally:
        if client:
            try:
                client.close()
            except:
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

@app.route('/api/documents/upload', methods=['POST'])
@token_required
def upload_document(current_user_id):
    """Upload and process a document for the knowledge base"""
    # Increase the max content length for this specific route
    from werkzeug.exceptions import RequestEntityTooLarge
    try:
        # Get form data
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            return jsonify({"error": "Title and content are required"}), 400
        
        # Get user info
        client = get_mongo_client()
        db = client["pharma_hub"]
        users_collection = db["users"]
        user = users_collection.find_one({"_id": ObjectId(current_user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Process document: Parse, clean, chunk, and prepare for embedding
        processed_content = process_document_content(content)
        
        # Upload document using internal agent
        doc_id = internal_agent.upload_document(
            title=title,
            text=processed_content,
            uploaded_by=user.get("email", "Unknown User")
        )
        
        return jsonify({
            "message": "Document uploaded and processed successfully",
            "doc_id": doc_id
        }), 200
        
    except RequestEntityTooLarge:
        return jsonify({"error": "File too large. Maximum size allowed is 16MB."}), 413
    except Exception as e:
        print(f"Error uploading document: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to upload document: {str(e)}"}), 500
    finally:
        if 'client' in locals():
            client.close()

def process_document_content(content):
    """Process document content: parse, clean, and chunk for embedding"""
    # Clean the content
    cleaned_content = clean_document_content(content)
    
    # Chunk the content for better embedding and retrieval
    chunks = chunk_document_content(cleaned_content)
    
    # For now, we'll store the cleaned content
    # In a full implementation, we would also generate embeddings here
    return cleaned_content

def clean_document_content(content):
    """Clean document content by removing extra whitespace and formatting"""
    import re
    
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Remove special characters that might interfere with processing
    content = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\\]', ' ', content)
    
    # Normalize quotation marks
    content = content.replace('"', '"').replace('"', '"')
    content = content.replace("'", "'").replace("'", "'")
    
    # Trim and return
    return content.strip()

def chunk_document_content(content, chunk_size=1000, overlap=200):
    """Chunk document content for better embedding and retrieval"""
    chunks = []
    
    # Simple chunking by sentences
    import re
    sentences = re.split(r'[.!?]+', content)
    
    current_chunk = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # If adding this sentence would exceed chunk size, save current chunk
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap
            words = current_chunk.split()
            overlap_words = words[-(overlap//5):] if len(words) > overlap//5 else []
            current_chunk = " ".join(overlap_words) + " " + sentence + " "
        else:
            current_chunk += sentence + ". "
    
    # Add the final chunk if it has content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

@app.route('/api/documents/chat', methods=['POST'])
@token_required
def chat_with_documents(current_user_id):
    """PharmaMind Nexus - Medical Knowledge Retrieval AI with Enhanced Analysis"""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Use the KnowledgeAgent for the complete pipeline
        response_text = knowledge_agent.run(query)
        
        return jsonify({
            "query": query,
            "response": response_text,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error in document chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to process chat request: {str(e)}"}), 500

def generate_pharmamind_nexus_response(query, results):
    """Generate an enhanced PharmaMind Nexus response combining document content with model analysis"""
    response_parts = []
    
    # 📄 1. Answer Based on Uploaded Documents
    doc_results = results.get('documents', {})
    doc_matches = doc_results.get('matches', []) if isinstance(doc_results, dict) else []
    
    response_parts.append("📄 1. Answer Based on Uploaded Documents")
    response_parts.append("")
    
    if doc_matches:
        # Extract exact sentences, sections, bullet points, tables or data directly from the documents
        doc_findings = []
        for i, match in enumerate(doc_matches[:5], 1):  # Up to 5 most relevant documents
            metadata = match.get('metadata', {}) if isinstance(match, dict) else {}
            title = metadata.get('title', f'Document {i}') if isinstance(metadata, dict) else f'Document {i}'
            text = metadata.get('text', 'No content available') if isinstance(metadata, dict) else 'No content available'
            
            # Limit text length for readability
            if len(text) > 300:
                text = text[:300] + "..."
            
            doc_findings.append(f"{i}. {title}: {text}")
        
        response_parts.append("\n".join(doc_findings))
    else:
        response_parts.append("No relevant information found in uploaded documents.")
    
    # 🔍 2. AI-Enhanced Analysis (combining document content with model reasoning)
    response_parts.append("")
    response_parts.append("🔍 2. AI-Enhanced Medical Analysis")
    response_parts.append("")
    
    # Perform deep analysis combining document content with medical knowledge
    analysis = perform_deep_medical_analysis(query, doc_matches, results)
    response_parts.append(analysis)
    
    # 📚 3. Sources Used
    response_parts.append("")
    response_parts.append("📚 Sources Used")
    response_parts.append("")
    
    if doc_matches:
        response_parts.append("From Your Documents:")
        for i, match in enumerate(doc_matches[:3], 1):
            metadata = match.get('metadata', {}) if isinstance(match, dict) else {}
            title = metadata.get('title', f'Document {i}') if isinstance(metadata, dict) else f'Document {i}'
            response_parts.append(f"{i}. {title}")
    else:
        response_parts.append("From Your Documents:")
        response_parts.append("No relevant documents found.")
    
    # Add external sources if used
    try:
        external_data = results.get('external', {})
        external_sources_added = False
        
        # Check what external data we have
        if external_data.get('trials'):
            if not external_sources_added:
                response_parts.append("")
                response_parts.append("External Medical Sources:")
                external_sources_added = True
            response_parts.append("• Clinical Trials Database")
        
        if external_data.get('pubmed'):
            if not external_sources_added:
                response_parts.append("")
                response_parts.append("External Medical Sources:")
                external_sources_added = True
            elif not external_sources_added:
                response_parts.append("• PubMed Database")
                
        if external_data.get('fda'):
            if not external_sources_added:
                response_parts.append("")
                response_parts.append("External Medical Sources:")
                external_sources_added = True
            response_parts.append("• FDA Database")
            
        if external_data.get('google'):
            if not external_sources_added:
                response_parts.append("")
                response_parts.append("External Medical Sources:")
                external_sources_added = True
            response_parts.append("• Google Search Results")
            
    except Exception as e:
        print(f"Error processing external sources: {e}")
    
    return "\n".join(response_parts) if response_parts else "No relevant information found."

def perform_deep_medical_analysis(query, doc_matches, results):
    """Perform deep medical analysis combining document content with model reasoning"""
    analysis_parts = []
    
    # If we have document content, analyze it deeply
    if doc_matches:
        # Extract document texts for analysis
        doc_texts = []
        for match in doc_matches:
            metadata = match.get('metadata', {}) if isinstance(match, dict) else {}
            text = metadata.get('text', '') if isinstance(metadata, dict) else ''
            if text:
                doc_texts.append(text)
        
        # Extract key medical concepts from documents
        key_concepts = extract_medical_concepts(doc_texts)
        
        # Analyze mechanisms of action if mentioned
        mechanisms = analyze_mechanisms_of_action(doc_texts)
        if mechanisms:
            analysis_parts.append("Mechanism of Action:")
            analysis_parts.append(mechanisms)
        
        # Analyze disease pathways if mentioned
        pathways = analyze_disease_pathways(doc_texts)
        if pathways:
            if mechanisms:
                analysis_parts.append("")
            analysis_parts.append("Disease Pathway Impact:")
            analysis_parts.append(pathways)
        
        # Analyze clinical evidence
        evidence = analyze_clinical_evidence(doc_texts)
        if evidence:
            if mechanisms or pathways:
                analysis_parts.append("")
            analysis_parts.append("Clinical Evidence Summary:")
            analysis_parts.append(evidence)
        
        # Analyze safety and contraindications
        safety = analyze_safety_profiles(doc_texts)
        if safety:
            if mechanisms or pathways or evidence:
                analysis_parts.append("")
            analysis_parts.append("Safety Profile:")
            analysis_parts.append(safety)
    
    # If we have external data, incorporate it
    external_insights = []
    external_data = results.get('external', {})
    
    # Add insights from clinical trials
    if external_data.get('trials'):
        trial_insights = analyze_clinical_trial_data(external_data['trials'])
        if trial_insights:
            external_insights.append(trial_insights)
    
    # Add insights from patents
    if external_data.get('patents'):
        patent_insights = analyze_patent_data(external_data['patents'])
        if patent_insights:
            external_insights.append(patent_insights)
    
    # Add insights from web intelligence
    if external_data.get('google') or external_data.get('pubmed'):
        web_data = external_data.get('google', []) + external_data.get('pubmed', [])
        web_insights = analyze_web_intelligence(web_data)
        if web_insights:
            external_insights.append(web_insights)
    
    if external_insights:
        if analysis_parts:
            analysis_parts.append("")
            analysis_parts.append("Additional Medical Insights:")
        else:
            analysis_parts.append("Medical Insights:")
        
        for insight in external_insights:
            analysis_parts.append(insight)
    
    # If no analysis was possible, provide a general medical context
    if not analysis_parts:
        general_context = provide_general_medical_context(query)
        analysis_parts.append(general_context)
    
    return "\n".join(analysis_parts)

def extract_medical_concepts(doc_texts):
    """Extract key medical concepts from document texts"""
    # In a full implementation, this would use NLP to extract medical entities
    # For now, we'll return a placeholder
    if doc_texts:
        return "Key medical concepts identified from document content."
    return ""

def analyze_mechanisms_of_action(doc_texts):
    """Analyze mechanisms of action mentioned in documents"""
    if not doc_texts:
        return ""
        
    # Look for keywords related to mechanisms of action
    mech_keywords = ['mechanism', 'inhibit', 'block', 'activate', 'bind', 'target', 'receptor', 'enzyme']
    relevant_excerpts = []
    
    for text in doc_texts:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in mech_keywords):
            # Find sentences containing keywords
            import re
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in mech_keywords):
                    relevant_excerpts.append(sentence.strip())
                    break  # Take first relevant sentence
    
    if relevant_excerpts:
        return "Based on document analysis, the mechanism involves " + relevant_excerpts[0][:100] + "..."
    return ""

def analyze_disease_pathways(doc_texts):
    """Analyze disease pathways mentioned in documents"""
    if not doc_texts:
        return ""
        
    # Look for keywords related to disease pathways
    pathway_keywords = ['pathway', 'cascade', 'signaling', 'metabolism', 'inflammation', 'immune response']
    relevant_excerpts = []
    
    for text in doc_texts:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in pathway_keywords):
            # Find sentences containing keywords
            import re
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in pathway_keywords):
                    relevant_excerpts.append(sentence.strip())
                    break  # Take first relevant sentence
    
    if relevant_excerpts:
        return "Document content indicates impact on " + relevant_excerpts[0][:100] + "..."
    return ""

def analyze_clinical_evidence(doc_texts):
    """Analyze clinical evidence mentioned in documents"""
    if not doc_texts:
        return ""
        
    # Look for keywords related to clinical evidence
    evidence_keywords = ['trial', 'study', 'efficacy', 'outcome', 'survival', 'response rate']
    relevant_excerpts = []
    
    for text in doc_texts:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in evidence_keywords):
            # Find sentences containing keywords
            import re
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in evidence_keywords):
                    relevant_excerpts.append(sentence.strip())
                    break  # Take first relevant sentence
    
    if relevant_excerpts:
        return "Clinical evidence from documents shows " + relevant_excerpts[0][:100] + "..."
    return ""

def analyze_safety_profiles(doc_texts):
    """Analyze safety profiles mentioned in documents"""
    if not doc_texts:
        return ""
        
    # Look for keywords related to safety
    safety_keywords = ['safety', 'tolerability', 'adverse', 'side effect', 'contraindication', 'toxicity']
    relevant_excerpts = []
    
    for text in doc_texts:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in safety_keywords):
            # Find sentences containing keywords
            import re
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in safety_keywords):
                    relevant_excerpts.append(sentence.strip())
                    break  # Take first relevant sentence
    
    if relevant_excerpts:
        return "Safety profile indicates " + relevant_excerpts[0][:100] + "..."
    return ""

def analyze_clinical_trial_data(trials):
    """Analyze clinical trial data for insights"""
    if not trials:
        return ""
    
    insights = []
    for trial in trials[:2]:  # Analyze top 2 trials
        title = trial.get('title', '')
        condition = trial.get('condition', 'N/A')
        phase = trial.get('phase', 'N/A')
        status = trial.get('status', 'N/A')
        insights.append(f"Clinical trial '{title}' for {condition} (Phase {phase}, {status}) provides evidence for this intervention.")
    
    return " ".join(insights)

def analyze_patent_data(patents):
    """Analyze patent data for insights"""
    if not patents:
        return ""
    
    insights = []
    for patent in patents[:2]:  # Analyze top 2 patents
        title = patent.get('title', '')
        assignee = patent.get('assignee', 'Unknown')
        insights.append(f"Patent '{title}' by {assignee} describes innovative approaches in this field.")
    
    return " ".join(insights)

def analyze_web_intelligence(web_data):
    """Analyze web intelligence for insights"""
    if not web_data:
        return ""
    
    insights = []
    for article in web_data[:2]:  # Analyze top 2 articles
        title = article.get('title', '')
        source = article.get('source', 'Source')
        insights.append(f"Recent research '{title}' from {source} contributes to current understanding.")
    
    return " ".join(insights)

def provide_general_medical_context(query):
    """Provide general medical context when specific analysis isn't possible"""
    return f"Based on medical knowledge, {query} involves complex biological processes that require professional medical evaluation. For specific guidance, consult with qualified healthcare professionals."

if __name__ == '__main__':
    print(f"Starting Pharma Mind Nexus API server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
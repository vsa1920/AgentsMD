import os
import sys
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from dotenv import load_dotenv
import werkzeug
import flask
import shutil
import threading
import re
import pdb
import sqlite3
sys.path.append(os.path.abspath(".."))
from SpeechToText import RecordingManager
from SpeechToText import assembly_request

# Add parent directory to path so we can import the AI Triage System
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import the AI Triage System
from ai_triage import ClinicalTriageSystem

# Add this at the top of your file
try:
    from werkzeug.urls import url_quote
except ImportError:
    # For newer Werkzeug versions
    from werkzeug.utils import url_quote

# Or if url_quote is completely removed, you can use urllib.parse
import urllib.parse

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Create output directories within the demo folder
os.makedirs("demo/quick_ref", exist_ok=True)
os.makedirs("demo/results", exist_ok=True)
os.makedirs("demo/discussions", exist_ok=True)

# Store the latest results for display
latest_results = {
    "case_id": None,
    "quick_ref_file": None,
    "detailed_output_file": None,
    "discussion_file": None,
    "differential_diagnoses_file": None
}

# Store progress updates
progress_updates = {
    "current_task": "Initializing...",
    "percentage": 0,
    "status": "pending",
    "message": ""
}

# Add this right after the imports
print(f"Flask version: {flask.__version__}")
print(f"Werkzeug version: {werkzeug.__version__}")

# Add this after creating the Flask app
recording_manager = RecordingManager()

# Set up SQLite database for conversation history
def init_db():
    conn = sqlite3.connect('demo/conversations.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        conversation_text TEXT NOT NULL,
        esi_level TEXT,
        case_id TEXT,
        summary TEXT
    )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Add this function to save a conversation
def save_conversation(conversation_text, esi_level=None, case_id=None, summary=None):
    """Save a conversation to the database"""
    # Don't save if there's no ESI level (processing not complete)
    if not esi_level:
        return None
        
    conn = sqlite3.connect('demo/conversations.db')
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # Ensure we have at least a basic summary if none is provided
    if not summary:
        summary = "Patient conversation (no summary available)"
    
    cursor.execute(
        'INSERT INTO conversations (timestamp, conversation_text, esi_level, case_id, summary) VALUES (?, ?, ?, ?, ?)',
        (timestamp, conversation_text, esi_level, case_id, summary)
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid

# Add this function to get all conversations
def get_all_conversations():
    """Get all conversations from the database"""
    conn = sqlite3.connect('demo/conversations.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Only get conversations with ESI levels
    cursor.execute('SELECT * FROM conversations WHERE esi_level IS NOT NULL ORDER BY timestamp DESC')
    conversations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return conversations

# Fix the get_conversation function
def get_conversation(conversation_id):
    """Get a specific conversation from the database"""
    conn = sqlite3.connect('demo/conversations.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
    
    # Only call fetchone() once and store the result
    result = cursor.fetchone()
    conversation = dict(result) if result else None
    
    conn.close()
    return conversation

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/progress')
def progress():
    """Server-sent events for progress updates"""
    def generate():
        while progress_updates["status"] == "pending":
            data = json.dumps({
                "task": progress_updates["current_task"],
                "percentage": progress_updates["percentage"],
                "message": progress_updates["message"]
            })
            yield f"data: {data}\n\n"
            time.sleep(0.5)
        
        # Send final update
        data = json.dumps({
            "task": progress_updates["current_task"],
            "percentage": 100,
            "message": progress_updates["message"],
            "status": progress_updates["status"]
        })
        yield f"data: {data}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

def process_case_task(patient_case, api_key, model="o1-mini"):
    """Background task to process the patient case"""
    try:
        # Reset progress
        progress_updates["current_task"] = "Initializing triage system..."
        progress_updates["percentage"] = 5
        progress_updates["status"] = "pending"
        progress_updates["message"] = f"Setting up the AI agents with {model}..."
        
        # Define a progress callback function
        def update_progress(message, percentage=None):
            if percentage is not None:
                progress_updates["percentage"] = percentage
            progress_updates["message"] = message
        
        # Initialize the triage system with the selected model
        triage_system = ClinicalTriageSystem(
            api_key=api_key,
            llm_backend=model,  # Use the selected model
            verbose=True
        )
        
        # Monkey patch the AgentDiscussion.deliberate method to capture progress
        original_deliberate = triage_system.discussion.deliberate
        
        def patched_deliberate(conversation_text, case_id=None):
            # Update the current task
            progress_updates["current_task"] = "Agent Discussion"
            
            # Call the original method with our progress callback
            return original_deliberate(
                conversation_text=conversation_text,
                case_id=case_id,
                progress_callback=update_progress
            )
        
        # Replace the method
        triage_system.discussion.deliberate = patched_deliberate
        
        # Process the conversation
        results = triage_system.process_conversation(patient_case)
        
        # Save the conversation with results
        save_conversation(
            conversation_text=patient_case,
            esi_level=results["esi_level"],
            case_id=results["case_id"],
            summary=results["justification"][:100] + "..."  # First 100 chars of justification as summary
        )
        
        # Update progress for file operations
        progress_updates["current_task"] = "Generating Output"
        progress_updates["percentage"] = 90
        progress_updates["message"] = "Creating output files..."
        
        case_id = results["case_id"]
        latest_results["case_id"] = case_id
        
        # Create demo directories
        os.makedirs("demo/quick_ref", exist_ok=True)
        os.makedirs("demo/results", exist_ok=True)
        os.makedirs("demo/discussions", exist_ok=True)
        
        # Copy quick reference files
        quick_ref_dir = "quick_ref"
        quick_ref_files = [f for f in os.listdir(quick_ref_dir) if f.startswith(case_id)]
        for file in quick_ref_files:
            src = os.path.join(quick_ref_dir, file)
            dst = os.path.join("demo/quick_ref", file)
            shutil.copy2(src, dst)
            latest_results["quick_ref_file"] = dst
        
        # Copy result files
        results_dir = "results"
        result_files = [f for f in os.listdir(results_dir) if f.startswith(case_id)]
        for file in result_files:
            src = os.path.join(results_dir, file)
            dst = os.path.join("demo/results", file)
            shutil.copy2(src, dst)
            if file.endswith(".txt"):
                latest_results["detailed_output_file"] = dst
        
        # Copy discussion files
        discussions_dir = "discussions"
        discussion_files = [f for f in os.listdir(discussions_dir) if f.startswith(case_id)]
        for file in discussion_files:
            src = os.path.join(discussions_dir, file)
            dst = os.path.join("demo/discussions", file)
            shutil.copy2(src, dst)
            latest_results["discussion_file"] = dst
        
        # Copy differential diagnoses files
        os.makedirs("demo/differential_diagnoses", exist_ok=True)
        differential_diagnoses_file = triage_system.generate_differential_diagnoses()
        if differential_diagnoses_file and os.path.exists(differential_diagnoses_file):
            dst = os.path.join("demo/differential_diagnoses", os.path.basename(differential_diagnoses_file))
            shutil.copy2(differential_diagnoses_file, dst)
            latest_results["differential_diagnoses_file"] = dst
        
        # Update progress
        progress_updates["current_task"] = "Complete"
        progress_updates["percentage"] = 100
        progress_updates["message"] = f"Triage assessment complete! ESI Level: {results['esi_level']}"
        progress_updates["status"] = "complete"
        
    except Exception as e:
        # Update progress with error
        progress_updates["current_task"] = "Error"
        progress_updates["percentage"] = 100
        progress_updates["message"] = str(e)
        progress_updates["status"] = "error"

@app.route('/process', methods=['POST'])
def process_case():
    """Process a patient case"""
    # Reset progress updates
    progress_updates["current_task"] = "Initializing..."
    progress_updates["percentage"] = 0  # Reset to 0
    progress_updates["status"] = "pending"
    progress_updates["message"] = ""
    
    # Get the patient case text from the form
    patient_case = request.form.get('conversation_text', '')
    
    # Get the selected model
    selected_model = request.form.get('model', 'o1-mini')
    
    if not patient_case:
        return jsonify({"error": "No patient case provided"}), 400
    
    # Get API key from environment - use OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        return jsonify({"error": "No OpenAI API key found in environment. Please set OPENAI_API_KEY in .env file."}), 400
    
    # Start processing in a background thread
    thread = threading.Thread(target=process_case_task, args=(patient_case, api_key, selected_model))
    thread.daemon = True
    thread.start()
    
    # Return immediately with a success message
    return jsonify({"success": True, "message": "Processing started"})

@app.route('/check_status')
def check_status():
    """Check the status of the processing"""
    if progress_updates["status"] == "complete":
        # Read the quick reference file for immediate display
        quick_ref_content = ""
        esi_level = None
        if latest_results["quick_ref_file"] and os.path.exists(latest_results["quick_ref_file"]):
            with open(latest_results["quick_ref_file"], 'r') as f:
                quick_ref_content = f.read()
                # Extract ESI level from the content
                esi_match = re.search(r'ESI LEVEL: (\d)', quick_ref_content)
                if esi_match:
                    esi_level = esi_match.group(1)
        
        return jsonify({
            "status": "complete",
            "case_id": latest_results["case_id"],
            "quick_ref": quick_ref_content,
            "esi_level": esi_level,
            "has_detailed_output": latest_results["detailed_output_file"] is not None,
            "has_discussion": latest_results["discussion_file"] is not None,
            "has_differential_diagnoses": latest_results["differential_diagnoses_file"] is not None
        })
    elif progress_updates["status"] == "error":
        return jsonify({
            "status": "error",
            "message": progress_updates["message"]
        })
    else:
        return jsonify({
            "status": "pending",
            "task": progress_updates["current_task"],
            "percentage": progress_updates["percentage"],
            "message": progress_updates["message"]
        })

@app.route('/view_detailed_output')
def view_detailed_output():
    """View the detailed output file"""
    if not latest_results["detailed_output_file"] or not os.path.exists(latest_results["detailed_output_file"]):
        return jsonify({"error": "No detailed output file available"}), 404
    
    with open(latest_results["detailed_output_file"], 'r') as f:
        content = f.read()
    
    return jsonify({"content": content})

@app.route('/view_discussion')
def view_discussion():
    """View the discussion file"""
    if not latest_results["discussion_file"] or not os.path.exists(latest_results["discussion_file"]):
        return jsonify({"error": "No discussion file available"}), 404
    
    with open(latest_results["discussion_file"], 'r') as f:
        content = f.read()
    
    return jsonify({"content": content})

@app.route('/view_differential_diagnoses')
def view_differential_diagnoses():
    """View the differential diagnoses file"""
    if not latest_results["differential_diagnoses_file"] or not os.path.exists(latest_results["differential_diagnoses_file"]):
        return jsonify({"error": "No differential diagnoses file available"}), 404
    
    with open(latest_results["differential_diagnoses_file"], 'r') as f:
        content = f.read()
    
    return jsonify({"content": content})

@app.route('/download/<file_type>')
def download_file(file_type):
    """Download a file"""
    if file_type == 'quick_ref' and latest_results["quick_ref_file"]:
        return send_file(
            latest_results["quick_ref_file"], 
            as_attachment=True,
            download_name=os.path.basename(latest_results["quick_ref_file"])
        )
    elif file_type == 'detailed_output' and latest_results["detailed_output_file"]:
        return send_file(
            latest_results["detailed_output_file"], 
            as_attachment=True,
            download_name=os.path.basename(latest_results["detailed_output_file"])
        )
    elif file_type == 'discussion' and latest_results["discussion_file"]:
        return send_file(
            latest_results["discussion_file"], 
            as_attachment=True,
            download_name=os.path.basename(latest_results["discussion_file"])
        )
    elif file_type == 'differential_diagnoses' and latest_results["differential_diagnoses_file"]:
        return send_file(
            latest_results["differential_diagnoses_file"], 
            as_attachment=True,
            download_name=os.path.basename(latest_results["differential_diagnoses_file"])
        )
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/recorder/start_recording', methods=['POST'])
def start_recording():
    success = recording_manager.start_recording()
    if success:
        return jsonify({"status": "success", "message": "Recording started"}), 200
    else:
        return jsonify({"status": "error", "message": "Recording already in progress"}), 400

@app.route('/recorder/stop_recording', methods=['POST'])
def stop_recording():
    # Create recordings directory if it doesn't exist
    os.makedirs('recordings', exist_ok=True)
    
    # Generate unique filename using timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recordings/audio.wav"
    
    success = recording_manager.stop_recording(filename)
    if success:
        return jsonify({
            "status": "success", 
            "message": "Recording stopped and saved",
            "filename": filename
        }), 200
    else:
        return jsonify({
            "status": "error", 
            "message": "No recording in progress"
        }), 400

@app.route('/recorder/recording_status', methods=['GET'])
def recording_status():
    is_recording = recording_manager.is_currently_recording()
    return jsonify({
        "status": "success",
        "is_recording": is_recording
    }), 200

@app.route('/transcriber/transcribe', methods=['POST'])
def transcribe_audio():
    # Create transcriptions directory if it doesn't exist
    os.makedirs('transcriptions', exist_ok=True)
    
    filename = f"recordings/audio.wav"
    transcription = assembly_request.transcribe_audio(filename, "transcriptions/transcription.txt")
    return jsonify({
        "status": "success",
        "transcription": transcription
    }), 200

# Add this endpoint to save a conversation
@app.route('/save_conversation', methods=['POST'])
def save_conversation_endpoint():
    """Save a conversation to the database"""
    data = request.json
    conversation_text = data.get('conversation_text')
    esi_level = data.get('esi_level')
    case_id = data.get('case_id')
    summary = data.get('summary')
    
    if not conversation_text:
        return jsonify({"error": "No conversation text provided"}), 400
    
    conversation_id = save_conversation(conversation_text, esi_level, case_id, summary)
    return jsonify({"success": True, "conversation_id": conversation_id}), 200

# Add this endpoint to get all conversations
@app.route('/get_conversations', methods=['GET'])
def get_conversations_endpoint():
    """Get all conversations from the database"""
    conversations = get_all_conversations()
    return jsonify({"conversations": conversations}), 200

# Add this endpoint to get a specific conversation
@app.route('/get_conversation/<int:conversation_id>', methods=['GET'])
def get_conversation_endpoint(conversation_id):
    """Get a specific conversation from the database"""
    conversation = get_conversation(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify({"conversation": conversation}), 200

# Add this endpoint to delete a conversation
@app.route('/delete_conversation/<int:conversation_id>', methods=['DELETE'])
def delete_conversation_endpoint(conversation_id):
    """Delete a conversation from the database"""
    conn = sqlite3.connect('demo/conversations.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Conversation deleted"}), 200

# Add this endpoint to delete all conversations
@app.route('/delete_all_conversations', methods=['DELETE'])
def delete_all_conversations_endpoint():
    """Delete all conversations from the database"""
    conn = sqlite3.connect('demo/conversations.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM conversations WHERE esi_level IS NOT NULL')
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "All conversations deleted"}), 200

# Add this endpoint to get prioritized patients
@app.route('/get_prioritized_patients', methods=['GET'])
def get_prioritized_patients_endpoint():
    """Get all conversations prioritized by ESI level"""
    conn = sqlite3.connect('demo/conversations.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all conversations with ESI levels
    cursor.execute('SELECT * FROM conversations WHERE esi_level IS NOT NULL ORDER BY timestamp DESC')
    conversations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Sort by ESI level (1 is highest priority)
    prioritized = sorted(conversations, key=lambda x: (
        int(x['esi_level']) if x['esi_level'] and x['esi_level'].isdigit() else 5,
        # Secondary sort by timestamp (most recent first)
        x['timestamp']
    ))
    
    return jsonify({"patients": prioritized}), 200

if __name__ == '__main__':
    # Run the app
    app.run(debug=True) 
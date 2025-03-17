# **Agents MD**

<p align="center">
  <img src="demo/static/images/AgentsMDLogo_2.jpeg" alt="Agents MD Logo" width="300">
</p>

Watching a loved one battle a disease is heartbreaking.

Watching them struggle in an overcrowded ER, waiting for care, is **devastating**.
 
Across the country, emergency rooms are in crisis—overcrowded, understaffed, and overwhelmed. Nurses face impossible workloads, making life-or-death decisions under extreme pressure, while patients endure agonizing delays in time-critical care.

Agents MD is transforming ER triage by addressing these urgent challenges. Our multi-agentic AI approach brings together competing AI models, each with specialized diagnostic expertise, to refine differential diagnoses in real time. By reducing diagnostic uncertainty and easing the burden on overworked nurses, we help accelerate patient care, enhance accuracy, and mirror the collaborative decision-making of medical teams—ensuring no patient is left waiting when every second counts.

## Our Solution

Agents MD leverages the power of large language models in a collaborative framework that mimics how medical professionals work together to reach consensus on patient care priorities. By combining multiple specialized AI agents, we create a system that is:

- **More accurate** than single-model approaches
- **Transparent** in its decision-making process
- **Supportive** of existing medical workflows
- **Responsive** to time-critical situations

## Installation

### Prerequisites
- Python 3.12.7
- pip 25.0
- Anaconda or Miniconda
- Git

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AgentsMD
   ```

2. **Set up Conda environment**
   ```bash
   conda create -n agents-md python=3.12.7
   conda activate agents-md
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**
   - We provide a template `dotEnv` file with the required API keys structure
   - Create your own `.env` file by copying the template:
     ```bash
     cp dotEnv .env
     ```
   - Get your API keys from:
     - [OpenAI](https://platform.openai.com/api-keys) - For AI models and diagnosis generation
     - [AssemblyAI](https://www.assemblyai.com/dashboard/signup) - For speech-to-text transcription
   - Replace the placeholder values in `.env` with your actual API keys:
     ```
     OPENAI_API_KEY="your-openai-api-key"
     ASSEMBLYAI_API_KEY="your-assemblyai-api-key"
     ```

## Running the Demo

1. **Navigate to the demo directory**
   ```bash
   cd demo
   ```

2. **Start the application**
   ```bash
   python app.py
   ```

3. **Access the web interface**
   - Open your web browser
   - Go to `http://127.0.0.1:5000` (the default Flask development server)
   
## Features

- Real-time speech-to-text transcription
- AI-powered triage assessment
- Differential diagnosis generation
- Case discussion and detailed output viewing
- Recording and transcription capabilities
- Patient prioritization system

## Important Notes

- Ensure all required API keys are properly set in your `.env` file
- The application creates directories for storing recordings, transcriptions, and other data
- The system uses SQLite for storing conversation history
- Make sure you have sufficient disk space for storing audio recordings and transcriptions